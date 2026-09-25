"""Offline file persistence and revision-safe studio issuance recovery."""
import calendar
import datetime as dt
import json
import math
import os
from pathlib import Path
import tempfile

import requests

from app.api import ApiError


def as_datetime(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    elif not isinstance(value, dt.datetime):
        value = dt.datetime.fromtimestamp(value, dt.timezone.utc)
    return value.replace(tzinfo=dt.timezone.utc) if value.tzinfo is None else value.astimezone(dt.timezone.utc)


def next_month(value):
    year = value.year + (value.month == 12)
    month = value.month % 12 + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=4)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_license(path):
    with open(path, encoding='utf-8') as stream:
        return json.loads(json.load(stream)['message'])


class PendingIssuance(Exception):
    pass


class AssignmentChanged(ApiError):
    def __init__(self):
        super().__init__(409, 'The machine assignment changed. Reload and explicitly activate again; a new activation consumes one month.')


class LicenseStore:
    def __init__(self, api, path, machine, hostname):
        self.api, self.path = api, Path(path)
        self.machine, self.hostname = machine, hostname
        self.pending_path = self.path.with_suffix(self.path.suffix + '.pending.json')

    def pending(self):
        if not self.pending_path.exists():
            return None
        with self.pending_path.open(encoding='utf-8') as stream:
            return json.load(stream)

    def _check_pending(self, pending, seat_id):
        if (pending['username'] != self.api.username or pending['base_url'] != self.api.base_url
                or pending['payload']['seat'] != seat_id or pending['payload']['machine'] != self.machine):
            raise PendingIssuance('Recover the pending license using its original account, server, and machine first.')

    def save(self, envelope, seat_id):
        # Preserve the exact signed message. Signature verification remains with
        # the existing Nemo license consumer; these checks prevent wrong-file saves.
        if not isinstance(envelope.get('message'), str) or not bytes.fromhex(envelope['signature']):
            raise ValueError('Invalid license envelope')
        data = json.loads(envelope['message'])
        if data['machine'] != self.machine or str(data['seat_id']) != str(seat_id):
            raise ValueError('The issued license does not match this machine and seat')
        for field in ('created_at', 'expires_at', 'refresh_at', 'to_renew_at'):
            if not isinstance(data[field], (int, float)) or not math.isfinite(data[field]):
                raise ValueError('Invalid license date')
        atomic_json(self.path, envelope)
        return data

    def download(self, seat):
        pending = self.pending()
        if pending:
            self._check_pending(pending, seat['id'])
            current = next((item for item in self.api.licenses() if item['id'] == seat['id']), None)
            if not current or current['revision'] == pending['payload']['expected_revision']:
                raise PendingIssuance('Issuance is not confirmed. Retry the same operation; its original revision will be reused.')
            if current['fingerprint'] != self.machine:
                # A different revision and binding prove the original request can
                # no longer commit. End recovery without spending or replacing the
                # local file; a new activation needs a separate user confirmation.
                self.pending_path.unlink(missing_ok=True)
                raise AssignmentChanged()
        data = self.save(self.api.download_license(seat['id']), seat['id'])
        if pending:
            self.pending_path.unlink(missing_ok=True)
        return data

    def issue(self, action, seat, replace_machine=False):
        payload = {'seat': seat['id']}
        if action == 'activate' or self.api.is_subaccount:
            payload['machine'] = self.machine
        if action == 'activate':
            payload['hostname'] = self.hostname
        created_pending = False
        if self.api.is_subaccount:
            payload['expected_revision'] = seat['revision']
            if action == 'activate':
                payload['replace_machine'] = replace_machine
            pending = self.pending()
            if pending:
                self._check_pending(pending, seat['id'])
                if pending['action'] != action:
                    raise PendingIssuance('Retry the original operation or download the current license first.')
                payload = pending['payload']
            else:
                atomic_json(self.pending_path, {
                    'username': self.api.username, 'base_url': self.api.base_url,
                    'action': action, 'payload': payload,
                })
                created_pending = True
        try:
            envelope = self.api.issue(action, payload)
        except (requests.RequestException, ApiError) as exc:
            if not self.api.is_subaccount:
                raise
            if isinstance(exc, ApiError) and exc.status < 500 and exc.status != 409:
                if created_pending:
                    self.pending_path.unlink(missing_ok=True)
                raise
            try:
                return self.download(seat)
            except AssignmentChanged:
                raise
            except (requests.RequestException, ApiError, PendingIssuance, ValueError, OSError):
                if created_pending and isinstance(exc, ApiError) and exc.status == 409:
                    # This response proves THIS request was rejected before debit.
                    # An older uncertain request must retain its original revision.
                    self.pending_path.unlink(missing_ok=True)
                    raise exc
                raise PendingIssuance('The request may have completed. Download the current license or retry the same operation; no new revision will be used.') from exc
        data = self.save(envelope, seat['id'])
        if self.api.is_subaccount:
            self.pending_path.unlink(missing_ok=True)
        return data

    def deactivate(self, seat):
        if self.api.is_subaccount:
            self.api.deactivate(seat['id'], expected_revision=seat['revision'])
        else:
            self.api.deactivate(seat['id'])
        # An unsuccessful server request must never delete the existing file.
        try:
            local_seat = read_license(self.path)['seat_id']
        except (OSError, ValueError, KeyError, TypeError):
            # Missing or unreadable local files do not prevent remote clearing.
            # Leave any file whose seat cannot be identified untouched.
            return
        if str(local_seat) == str(seat['id']):
            self.path.unlink()

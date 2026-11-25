from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from .http_client import FetchError


class RollbackError(OSError):
    """Output recovery failed; backup files must be retained."""


def check_ninisite_pilot_permission(pilot):
    """Allow only the fixed one-topic pilot requested by the user."""
    from .ninisite_pilot import NiniSitePilot, ROBOTS, TOPIC
    if (type(pilot) is not NiniSitePilot or pilot.permission_status != 'User-authorized one-topic inspection'
            or pilot.topic_url != TOPIC or pilot.robots_url != ROBOTS):
        raise PermissionError('Source is not approved')


def check_ninisite_continuous_permission(collector):
    """Permit only the user-requested filtered first-page collector."""
    from .ninisite_continuous import ContinuousNiniSiteCollector
    if (type(collector) is not ContinuousNiniSiteCollector
            or collector.permission_status != 'User-authorized filtered first-page'):
        raise PermissionError('Source is not approved')


class Connector(ABC):
    identifier: str
    source_url: str
    permission_status: str

    def check_permission(self):
        # Approval is tied to this exact implementation and endpoint, not input.
        if (type(self) is not WorldBankConnector
                or getattr(self, 'permission_status', None) != 'Approved'
                or getattr(self, 'identifier', None) != 'world-bank-female-labor-force'
                or getattr(self, 'source_url', None) != WORLD_BANK_URL):
            raise PermissionError('Source is not approved')

    def run(self, client, output_dir):
        self.check_permission()
        records = self.normalize(self.validate(self.retrieve(client)))
        self.save(records, output_dir)
        return records

    @abstractmethod
    def retrieve(self, client): ...
    @abstractmethod
    def validate(self, payload): ...
    @abstractmethod
    def normalize(self, data): ...
    @abstractmethod
    def save(self, records, output_dir): ...


class Observation(BaseModel):
    model_config = ConfigDict(extra='ignore', allow_inf_nan=False)
    indicator: dict
    countryiso3code: str
    date: str = Field(pattern=r'^\d{4}$')
    value: float | None

    @field_validator('value', mode='before')
    @classmethod
    def validate_value(cls, value):
        if value is None:
            return None
        if type(value) not in (int, float):
            raise ValueError('must be a finite JSON number or null')
        try:
            if not math.isfinite(value):
                raise ValueError('must be a finite JSON number or null')
        except OverflowError:
            raise ValueError('must be a finite JSON number or null') from None
        return value


WORLD_BANK_URL = 'https://api.worldbank.org/v2/country/IRN/indicator/SL.TLF.ACTI.FE.ZS?format=json&per_page=1000'


class WorldBankConnector(Connector):
    identifier = 'world-bank-female-labor-force'
    source_url = WORLD_BANK_URL
    permission_status = 'Approved'

    def retrieve(self, client):
        self.check_permission()
        try:
            return client.get(self.source_url, self.identifier).json()
        except ValueError:
            raise FetchError('invalid_json') from None

    def validate(self, payload):
        try:
            if not isinstance(payload, list) or len(payload) != 2:
                raise ValueError()
            meta, rows = payload
            if not isinstance(meta, dict) or meta.get('pages') != 1 or not isinstance(rows, list) or not rows:
                raise ValueError()
            if meta.get('total') != len(rows):
                raise ValueError()
            result = []
            for index, row in enumerate(rows):
                try:
                    result.append(Observation.model_validate(row))
                except ValidationError as exc:
                    field = '.'.join(str(x) for x in exc.errors()[0]['loc']) or 'record'
                    raise FetchError(f'invalid_response record={index} field={field}') from None
            if any(x.indicator.get('id') != 'SL.TLF.ACTI.FE.ZS' or x.countryiso3code != 'IRN' for x in result):
                raise ValueError()
            if len({x.date for x in result}) != len(result):
                raise ValueError()
            return result
        except (TypeError, ValueError, ValidationError):
            raise FetchError('invalid_response') from None

    def normalize(self, data):
        timestamp = datetime.now(timezone.utc).isoformat()
        return [dict(source='World Bank World Development Indicators', source_url=self.source_url,
                     indicator_id='SL.TLF.ACTI.FE.ZS', indicator_label=x.indicator.get('value'),
                     country_code='IRN', year=int(x.date), value=x.value, retrieved_at=timestamp,
                     attribution='World Bank, World Development Indicators; ILO modeled estimates',
                     license_reference='https://creativecommons.org/licenses/by/4.0/',
                     license_terms='https://datacatalog.worldbank.org/public-licenses') for x in data]

    def save(self, records, output_dir):
        # Complete both serializations before touching any destination.
        json_text = json.dumps(records, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        jsonl_text = ''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in records)
        target = Path(output_dir) / 'processed'
        target.mkdir(parents=True, exist_ok=True)
        destinations = [target / 'world-bank-female-labor-force.json', target / 'world-bank-female-labor-force.jsonl']
        temps, backups, replaced = [], {}, []
        preserve_backups = False

        def stage(content, prefix='.world-bank-stage-'):
            with tempfile.NamedTemporaryFile(mode='wb', dir=target, prefix=prefix, suffix='.tmp', delete=False) as f:
                name = Path(f.name)
                temps.append(name)
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            return name

        try:
            staged = [stage(text.encode('utf-8')) for text in (json_text, jsonl_text)]
            # Backups are independent copies, so destinations remain untouched until commit.
            for destination in destinations:
                if destination.exists():
                    backups[destination] = stage(destination.read_bytes(), prefix=f'.world-bank-backup-{destination.suffix[1:]}-')
            try:
                for src, dst in zip(staged, destinations):
                    os.replace(src, dst)
                    replaced.append(dst)
            except OSError as original:
                failures = []
                for dst in reversed(replaced):
                    try:
                        if dst in backups:
                            os.replace(backups[dst], dst)
                        else:
                            dst.unlink(missing_ok=True)
                    except OSError:
                        failures.append(dst.name)
                if failures:
                    preserve_backups = True
                    raise RollbackError('Output rollback failed; backups retained in processed directory for manual recovery') from original
                raise
        finally:
            for path in temps:
                if preserve_backups and path in backups.values():
                    continue
                path.unlink(missing_ok=True)

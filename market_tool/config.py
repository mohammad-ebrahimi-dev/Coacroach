import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    http_proxy: str | None = Field(default=None, exclude=True, repr=False)
    https_proxy: str | None = Field(default=None, exclude=True, repr=False)
    http_timeout: float = Field(default=15, gt=0, le=300)
    connect_timeout: float | None = Field(default=None, gt=0, le=300)
    read_timeout: float | None = Field(default=None, gt=0, le=300)
    write_timeout: float | None = Field(default=None, gt=0, le=300)
    pool_timeout: float | None = Field(default=None, gt=0, le=300)
    max_retries: int = Field(default=2, ge=0, le=5)
    output_dir: Path = Path('data')
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO'

    @field_validator('http_proxy', 'https_proxy', mode='before')
    @classmethod
    def valid_proxy(cls, value):
        if value is None or not str(value).strip():
            return None
        value = str(value).strip()
        try:
            parts = urlsplit(value)
            if parts.scheme not in ('http', 'https') or not parts.hostname or parts.port is None:
                raise ValueError()
        except ValueError:
            raise ValueError('Proxy must be an HTTP(S) URL with host and port') from None
        return value

    @classmethod
    def load(cls, env_file='.env'):
        local = dotenv_values(env_file)
        values = {}
        for name in cls.model_fields:
            key = name.upper()
            value = os.environ.get(key, local.get(key))
            if value is not None and (value != '' or name in ('http_proxy', 'https_proxy')):
                values[name] = value
        return cls(**values)

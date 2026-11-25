import argparse
import logging
from pathlib import Path
from pydantic import ValidationError
from market_tool.config import Settings
from market_tool.connectors import RollbackError, WorldBankConnector
from market_tool.http_client import FetchError, HttpClient


def main():
    parser = argparse.ArgumentParser(description='Approved-source market research collector')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list-sources')
    commands.add_parser('test-connection')
    fetch = commands.add_parser('fetch')
    fetch.add_argument('source', choices=['world-bank-female-labor-force'])
    args = parser.parse_args()
    try:
        settings = Settings.load()
    except (ValidationError, ValueError):
        print('Invalid configuration; check .env and environment variables. Values are not displayed.')
        return 2
    Path('logs').mkdir(exist_ok=True)
    for name in ('raw', 'processed'):
        (settings.output_dir / name).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename='logs/collector.log', level=getattr(logging, settings.log_level),
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    logging.getLogger('httpx').setLevel(logging.CRITICAL)
    logging.getLogger('httpcore').setLevel(logging.CRITICAL)
    connector = WorldBankConnector()
    if args.command == 'list-sources':
        print(f'{connector.identifier}: {connector.permission_status} (Iran; SL.TLF.ACTI.FE.ZS)')
        return 0
    client = HttpClient(settings)
    try:
        if args.command == 'test-connection':
            connector.check_permission()
            response = client.get(connector.source_url, connector.identifier)
            print(f'HTTP {response.status_code}; response body not saved')
        else:
            records = connector.run(client, settings.output_dir)
            print(f'Saved {len(records)} aggregate observations to {settings.output_dir / "processed"}')
        return 0
    except (FetchError, PermissionError) as exc:
        print(f'Request failed: {exc}. See logs/collector.log for request diagnostics.')
        return 1
    except RollbackError:
        print('Output rollback failed; outputs may differ. Backups are retained in the processed directory for manual recovery.')
        return 1
    except (OSError, ValueError):
        print('Output or configuration error; no sensitive details displayed.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

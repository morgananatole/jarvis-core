#!/usr/bin/env python3
"""Read-only setup checks and private checkpoints. No tokens or phone numbers accepted."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installation_journal import audit, append, plan, STEPS, RESULTS


class PrivateParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Argumentos inválidos. Use --help; não inclua credenciais ou dados pessoais.\n')


def main():
    parser = PrivateParser(description='PULSE: roteiro e diário de instalação sem segredos')
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ('plan', 'check'):
        p = subs.add_parser(name)
        p.add_argument('--case', choices=['new_device', 'new_company', 'current_number'], required=True)
        p.add_argument('--number-state', choices=['cloud_api', 'business_app', 'new', 'unknown'], required=True)
        p.add_argument('--goal', choices=['pulse', 'coexistence'], required=True)
        if name == 'check':
            p.add_argument('--base-url', required=True)
            p.add_argument('--out', required=True, help='Arquivo privado .jsonl; não colocar no Git')
    p = subs.add_parser('record')
    p.add_argument('--out', required=True)
    p.add_argument('--run-id', required=True)
    p.add_argument('--step', choices=sorted(STEPS), required=True)
    p.add_argument('--result', choices=sorted(RESULTS), required=True)
    p.add_argument('--evidence', default='{}', help='JSON só com campos técnicos permitidos; sem texto livre')
    p.add_argument('--duration-seconds', type=float, default=0)
    args = parser.parse_args()
    try:
        if args.command == 'plan':
            result = plan(args.case, args.number_state, args.goal)
        elif args.command == 'check':
            result = audit(args.base_url, args.case, args.number_state, args.goal, args.out)
        else:
            result = append(args.out, args.run_id, args.step, args.result,
                json.loads(args.evidence), args.duration_seconds)
    except Exception:
        print(json.dumps({'error': 'invalid_or_unavailable_installation_check',
            'next_action': 'Conferir argumentos permitidos e arquivo privado; não incluir segredos.'}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

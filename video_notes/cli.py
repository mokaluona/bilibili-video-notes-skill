import argparse
import json
from .config import load, require
from .pipeline import batch
from .reviews import request, import_result
from .quality import report

def main():
    parser = argparse.ArgumentParser(description="Video notes: experimental modular orchestration")
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("run")
    p.add_argument("--run", action="append", required=True)
    p.add_argument("--until", choices=["preflight", "candidates", "sample", "final", "deliver", "completed"], default="candidates")
    p = subs.add_parser("convert")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p = subs.add_parser("build")
    p.add_argument("--document", required=True)
    p.add_argument("--assets", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--style")
    p.add_argument("--sample", action="store_true")
    for name in ("review-request", "review-import", "validate", "build-run", "render", "diagnose", "delivery-plan", "deliver", "cleanup"):
        p = subs.add_parser(name)
        p.add_argument("--run", required=True)
        if name in ("review-request", "review-import"):
            p.add_argument("--kind", choices=["vision", "content", "page", "sample_page"], required=True)
        if name in ('build-run', 'render'):
            p.add_argument('--sample', action='store_true')
        if name == 'cleanup':
            p.add_argument('--execute', action='store_true')
        if name == 'deliver':
            p.add_argument('--recover', action='store_true')
        if name == "review-import":
            p.add_argument("--input", required=True)
    for name in ('contacts', 'select', 'supplement', 'excerpt', 'freeze-topics'):
        p = subs.add_parser(name)
        p.add_argument('--run', required=True)
        if name == 'select':
            p.add_argument('--input', required=True)
        if name == 'supplement':
            p.add_argument('--seconds', type=float, required=True)
        if name == 'excerpt':
            p.add_argument('--start', type=float, required=True)
            p.add_argument('--end', type=float, required=True)
    args = parser.parse_args()
    try:
        if args.command == "convert":
            from .legacy import convert
            from .storage import read, write
            write(args.output, convert(read(args.input)))
            result = {"output": args.output}
        elif args.command == "build":
            from .document import build, StyleProfile
            from .storage import read
            result = build(read(args.document), args.output, args.assets,
                           StyleProfile(**read(args.style)) if args.style else None, args.sample)
        elif args.command == "run":
            result = batch([load(x) for x in args.run], args.until)
        else:
            run = load(args.run)
            stage = args.command
            if stage in ('review-request', 'review-import') and args.kind == 'content':
                missing = [f for f in ('topics', 'document') if not run.get(f)]
                if missing:
                    raise ValueError('Review content missing fields: ' + ', '.join(missing))
            require(run, stage)
            from .rendering import build_run, render
            from .diagnostics import diagnostic
            from .delivery import plan, deliver
            from .retention import plan as cleanup_plan, execute as cleanup_execute
            from .selection import contacts, select, supplement, excerpt
            from .topics import freeze
            actions = {'review-request': lambda: request(run, args.kind), 'review-import': lambda: import_result(run, args.kind, args.input),
                       'validate': lambda: report(run), 'build-run': lambda: build_run(run, args.sample), 'render': lambda: render(run, args.sample),
                       'diagnose': lambda: diagnostic(run), 'delivery-plan': lambda: plan(run), 'deliver': lambda: deliver(run, args.recover),
                       'cleanup': lambda: cleanup_execute(run) if args.execute else cleanup_plan(run)}
            actions.update({'contacts': lambda: contacts(run), 'select': lambda: select(run, args.input),
                            'supplement': lambda: supplement(run, args.seconds), 'excerpt': lambda: excerpt(run, args.start, args.end),
                            'freeze-topics': lambda: freeze(run)})
            from .locks import guarded
            result = actions[args.command]() if args.command == 'excerpt' else guarded(lambda active_run: actions[args.command]())(run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if isinstance(result, list) and any(x.get("status") == "failed" for x in result):
            raise SystemExit(1)
        if isinstance(result, dict) and result.get("decision") == "blocked":
            raise SystemExit(2)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"{type(error).__name__}: {error}\n")

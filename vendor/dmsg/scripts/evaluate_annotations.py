"""Only prints measured statistics for user-supplied labeled JSONL, no demo accuracy fabrication.

Usage: python scripts/evaluate_annotations.py /path/to/annotated.jsonl
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prototype.evaluation_gate import evaluate,EvaluationError

def main(argv):
    if len(argv)!=2:
        print('USAGE: python scripts/evaluate_annotations.py <existing_annotations.jsonl>')
        return 2
    path=Path(argv[1]);rows=[]
    if not path.is_file():
        print('NOT_RUN: ANNOTATIONS_FILE_MISSING')
        return 2
    try:
        if path.stat().st_size>1000000:raise EvaluationError('INPUT_TOO_LARGE')
        for line in path.read_text(encoding='utf8').splitlines():
            if line.strip(): rows.append(json.loads(line))
        print(json.dumps(evaluate(rows),ensure_ascii=False,indent=2,sort_keys=True))
        return 0
    except (ValueError,UnicodeError,EvaluationError) as exc:
        print('INVALID_EVALUATION_INPUT: '+str(exc))
        return 2

if __name__=='__main__':sys.exit(main(sys.argv))

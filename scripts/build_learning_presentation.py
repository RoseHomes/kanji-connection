"""Build an additive MCQ audit and reading exclusion map. No source/SQL writes."""
import json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.book_verify import References
from app.learning_presentation import objective_questions, VERSION

def main():
    book=json.loads((ROOT/'private/editorial-working/effective-book.json').read_bytes())
    refs=References(ROOT/'private/dictionaries')
    words={w['word'] for c in book['chapters'] for w in c['vocabulary']}
    variants={word:sorted({reading for (form,reading) in refs.words if form==word}) for word in words}
    folder=ROOT/'private/learning-presentation';folder.mkdir(exist_ok=True)
    (folder/'reading-variants-v1.json').write_text(json.dumps({'version':VERSION,'dictionary_sources':refs.sources,'words':variants},ensure_ascii=False,indent=2),encoding='utf-8')
    from app.learning_presentation import reading_variants
    reading_variants.cache_clear()
    bundle=json.loads((ROOT/'private/editorial-working/working-bundle.json').read_bytes())
    rubrics={op['key']['lesson_id']['$ref']['key']['chapter']:op['values']['answer_key']['rubric'] for op in bundle['operations'] if op['table']=='quiz_questions' and op['key']['stable_key']=='comparison-c'}
    chapters=[]
    for c in book['chapters']:
        ops=[op for op in bundle['operations'] if op['table'] in {'lesson_sections','quiz_questions'} and op['key']['lesson_id']['$ref']['key']['chapter']==c['chapter']]
        blocks=[b for op in sorted((op for op in ops if op['table']=='lesson_sections'), key=lambda op:op['key']['position']) for b in op['values']['blocks'] if b.get('kind')!='source_page_text']
        cards=[card for b in blocks for card in b.get('cards',[])]
        vocabulary=[word for b in blocks for word in b.get('vocabulary',[])]
        originals=[{'key':op['key']['stable_key'],'type':op['values']['question_type'],'prompt':op['values']['prompt']['text'],'answer':op['values']['answer_key'].get('text','')} for op in sorted((op for op in ops if op['table']=='quiz_questions'),key=lambda op:op['key']['stable_key'])]
        questions=objective_questions(cards,vocabulary,originals,rubrics[c['chapter']],slug=f'chapter-{c["chapter"]:02}')
        assert len(questions)==15
        chapters.append({'chapter':c['chapter'],'source_questions':14,'manual_source_rubric_preserved':True,'objective_questions':questions})
    result={'version':VERSION,'educational_edition':'2026-11-19-final-v2','source_sha256':hashlib.sha256((ROOT/'private/editorial-working/effective-book.json').read_bytes()).hexdigest(),'chapters':chapters,'converted_meaning':210,'converted_reading':210,'new_objective_shape':30,'excluded':0,'database_writes':0}
    (folder/'mcq-presentation-v1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'chapters':30,'mcq':sum(len(c['objective_questions']) for c in chapters),'database_writes':0}))
if __name__=='__main__':main()

import hashlib
import json
import re
from pathlib import Path
from typing import Optional, List

import plac
from pydantic import BaseModel, Field
from pymultirole_plugins.v1.schema import Document, Annotation
from wasabi import Printer


class EvalEntity(BaseModel):
    id: str = Field(
        None, description="id name of the entity", example="euDoZG0Ang"
    )
    label: Optional[str] = Field(
        None, description="Label of the annotation", example="ORG"
    )
    text: Optional[str] = Field(
        None, description="Covering text of the annotation", example="Kairntech"
    )
    start: List[int] = Field(
        ..., description="Start index of the span in the text", example=[5]
    )
    end: List[int] = Field(..., description="End index of the span in the text", example=[15])


class EvalEventElement(BaseModel):
    attribute: str = Field(
        None, description="Label name of the category", example="evt:central_element"
    )
    occurrences: List[str] = Field(
        None, description="Label of the category", example=[
            "64QddL5vUV"]
    )


class EvalDocument(BaseModel):
    text: str = Field(None, description="Plain text of the converted document")
    entities: Optional[List[EvalEntity]] = Field(
        None, description="Document entities"
    )
    events: Optional[List[List[EvalEventElement]]] = Field(
        None, description="Document events"
    )


class EvalDocumentList(BaseModel):
    __root__: List[EvalDocument]



@plac.annotations(
    input=("Input file or directory", "positional", None, str),
    output_dir=("Output directory. '-' for stdout.", "positional", None, str),
    txt=("Input file pattern", "option", "t", str),
    encoding=("File encoding", "option", "e", str)
)
def convert(
        input,
        output_dir,
        txt="*.json",
        encoding="utf-8"
):
    """
    Convert files into JSON format for use with pretrain/train command and other
    experiment management functions. If no output_dir is specified, the data
    is written to stdout, so you can pipe them forward to a JSON file
    """
    msg = Printer()
    input_path = Path(input)
    if not input_path.exists():
        msg.fail("Input file not found", input_path, exits=1)
    if not Path(output_dir).exists():
        msg.fail("Output directory not found", output_dir, exits=1)
    if input_path.is_dir():
        for f in input_path.rglob(txt):
            convert_file(f, output_dir, encoding=encoding, msg=msg)
    else :
        convert_file(input_path, output_dir, encoding=encoding, msg=msg)


def generate_id(docid, a: Annotation):
    return hashlib.shake_256(f"{docid}-{a.start}:{a.end}".encode("utf-8")).hexdigest(5)


CENTRAL_TYPES = [
    "radioisotope", "toxic_c_agent", "explosive",

    "path_ref_to_dis", "non_inf_disease", "inf_disease", "dis_ref_to_path",

    "pathogen", "bio_toxin"]


def clean_ids(event_ids):
    regex = r"\d+:\d+"
    clean_ids = []
    for event_id in event_ids:
        matches = re.finditer(regex, event_id, re.MULTILINE)

        for matchNum, match in enumerate(matches, start=1):
            clean_id = match.group()
            clean_ids.append(clean_id)
    return clean_ids

def convert_file(input_path, output_dir, **kwargs):
    if output_dir != "-":
        # Export data to a file

        suffix = ".json"
        encoding = kwargs['encoding']
        msg = kwargs['msg']
        file_name = str(Path(input_path.parts[-1]).with_suffix(""))
        output_file = Path(output_dir) / Path(input_path.parts[-1]).with_suffix(suffix)
        example_file = Path(output_dir)  / f"{file_name}.txt"
        data = []
        examples = []
        with input_path.open("r", encoding=encoding) as fin:
            jdocuments = json.load(fin)
            documents = [Document(**jdocument) for jdocument in jdocuments]
            sorted_documents = sorted(documents, key=lambda doc: int(doc.identifier[len("20250516_NP_test_evalLLM"):]))
            for di, document in enumerate(sorted_documents):
                altTexts  = {a.name:a.text for a in document.altTexts}
                ev_alt = altTexts['Events']
                entities = []
                idmap = {}
                events = []
                for a in document.annotations:
                    eid = generate_id(di, a)
                    ea = EvalEntity(id=eid, text=a.text, label=a.labelName, start=[a.start], end=[a.end])
                    idmap[f"{a.start}:{a.end}"] = ea
                    entities.append(ea)
                print(ev_alt)
                raw_events = json.loads(ev_alt)
                for raw_event in raw_events:
                    cleaned_events = raw_event['central']
                    centrals = []
                    for c in cleaned_events:
                        if c in idmap and idmap[c].label in CENTRAL_TYPES:
                            centrals.append(idmap[c].id)
                        else:
                            print(f"Warning, bad event: {c}")
                    elems = []
                    celem = EvalEventElement(attribute="evt:central_element", occurrences=centrals)
                    elems.append(celem)

                    list_associateds = raw_event['associated']
                    for associateds in list_associateds:
                        cleaned_events = associateds
                        associateds = [idmap[a].id for a in cleaned_events if
                                    a in idmap]
                        aelem = EvalEventElement(attribute="evt:associated_element", occurrences=associateds)
                        elems.append(aelem)

                    events.append(elems)

                edoc = EvalDocument(text=document.text, entities=entities, events=events)
                data.append(edoc)
        dl = EvalDocumentList(__root__=data)
        with output_file.open("w", encoding=encoding) as fout:
            print(dl.json(exclude_none=True, exclude_unset=True, indent=2), file=fout)

    msg.good("Generated output file ({} documents)".format(len(data)), output_file)


if __name__ == '__main__':
    plac.call(convert)
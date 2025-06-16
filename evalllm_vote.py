import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Optional, List

import plac
from pydantic import BaseModel, Field
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
    input1=("Input file or directory", "positional", None, str),
    input2=("Input file or directory", "positional", None, str),
    output_dir=("Output directory. '-' for stdout.", "positional", None, str),
    encoding=("File encoding", "option", "e", str)
)
def convert(
        input1,
        input2,
        output_dir,
        encoding="utf-8"
):
    """
    Convert files into JSON format for use with pretrain/train command and other
    experiment management functions. If no output_dir is specified, the data
    is written to stdout, so you can pipe them forward to a JSON file
    """
    msg = Printer()
    input1_path = Path(input1)
    if not input1_path.exists():
        msg.fail("Input file not found", input1_path, exits=1)
    input2_path = Path(input2)
    if not input2_path.exists():
        msg.fail("Input file not found", input2_path, exits=1)
    if not Path(output_dir).exists():
        msg.fail("Output directory not found", output_dir, exits=1)
    convert_file(input1_path, input2_path, output_dir, encoding=encoding, msg=msg)


def convert_file(input1_path, input2_path, output_dir, **kwargs):
    if output_dir != "-":
        # Export data to a file
        suffix = ".json"
        encoding = kwargs['encoding']
        msg = kwargs['msg']
        file_name1 = str(Path(input1_path.parts[-1]).with_suffix(""))
        file_name2 = str(Path(input2_path.parts[-1]).with_suffix(""))
        output_file = Path(output_dir) / f"{file_name1}_{file_name2}_vote.json"
        data = []
        with input1_path.open("r", encoding=encoding) as fin1:
            with input2_path.open("r", encoding=encoding) as fin2:
                jevaldocuments1 = [EvalDocument(**jdoc) for jdoc in json.load(fin1)]
                jevaldocuments2 = [EvalDocument(**jdoc) for jdoc in json.load(fin2)]
                for doc1, doc2 in zip(jevaldocuments1, jevaldocuments2):
                    new_doc = deepcopy(doc1)
                    evmap = defaultdict(set)
                    for ev1, event1 in enumerate(doc1.events):
                        for ev2, event2 in enumerate(doc2.events):
                            for el1, elem1 in enumerate(event1):
                                for el2, elem2 in enumerate(event2):
                                    evmap[(ev1, ev2, el1, el2)] = set(elem1.occurrences) & set(elem2.occurrences)
                    events = defaultdict(list)
                    for evidx, occsets in evmap.items():
                        ev1, ev2, el1, el2 = evidx
                        if el1 == 0 and el2 == 0 and len(occsets) > 0:
                            events[(ev1, ev1)].append(EvalEventElement(attribute='evt:central_element', occurrences=list(occsets)))
                        if el1 != 0 and el2 != 0 and len(occsets) > 0:
                            if len(events[(ev1, ev1)]) > 0:
                                events[(ev1, ev1)].append(
                                    EvalEventElement(attribute='evt:associated_element', occurrences=list(occsets)))
                    new_doc.events = list(events.values())
                    data.append(new_doc)
        dl = EvalDocumentList(__root__=data)
        with output_file.open("w", encoding=encoding) as fout:
            print(dl.json(exclude_none=True, exclude_unset=True, indent=2), file=fout)

    msg.good("Generated output file ({} documents)".format(len(data)), output_file)


if __name__ == '__main__':
    plac.call(convert)
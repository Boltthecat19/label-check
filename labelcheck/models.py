from enum import StrEnum

from pydantic import BaseModel, Field


class Status(StrEnum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"
    NOT_CHECKED = "NOT_CHECKED"


class BeverageType(StrEnum):
    spirits = "spirits"
    wine = "wine"
    beer = "beer"


class Application(BaseModel):
    """The fields an agent reads off the COLA application."""

    brand: str
    class_type: str = ""
    abv_percent: float | None = None
    net_contents: str = ""
    bottler: str = ""
    is_import: bool = False
    origin_country: str = ""
    beverage_type: BeverageType = BeverageType.spirits
    application_id: str = ""
    image: str = ""  # batch mode: filename of the label image


class FieldResult(BaseModel):
    field: str
    status: Status
    expected: str = ""
    found: str = ""
    confidence: float = 0.0
    note: str = ""


class Verdict(BaseModel):
    application_id: str = ""
    results: list[FieldResult] = Field(default_factory=list)
    overall: Status = Status.REVIEW
    ocr_text: str = ""
    processing_ms: int = 0
    warnings: list[str] = Field(default_factory=list)

    @staticmethod
    def overall_from(results: list[FieldResult]) -> Status:
        checked = [r.status for r in results if r.status != Status.NOT_CHECKED]
        if any(s == Status.FAIL for s in checked):
            return Status.FAIL
        if any(s == Status.REVIEW for s in checked):
            return Status.REVIEW
        return Status.PASS

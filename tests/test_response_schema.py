from app.models.common import ErrorDetail, ErrorResponse, PageData, SuccessResponse
from app.models.tweet import Tweet


def test_success_page_schema_is_stable() -> None:
    page = PageData[Tweet](
        items=[], next_cursor="NEXT", has_more=True, pagination_complete=False
    )
    response = SuccessResponse[PageData[Tweet]](data=page)
    assert response.model_dump() == {
        "ok": True,
        "data": {
            "items": [],
            "next_cursor": "NEXT",
            "has_more": True,
            "pagination_complete": False,
            "pagination_issue": None,
        },
    }


def test_error_schema_is_stable() -> None:
    response = ErrorResponse(error=ErrorDetail(code="x", message="safe"))
    assert response.model_dump() == {
        "ok": False,
        "error": {"code": "x", "message": "safe"},
    }

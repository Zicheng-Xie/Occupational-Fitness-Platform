from tools import docling_extension_audit as audit


def test_native_bottom_left_boxes_align_with_original_top_left_regions():
    assert audit.top_left_bbox(
        {"l": 20, "r": 80, "t": 750, "b": 710, "coord_origin": "BOTTOMLEFT"}, 800
    ) == [20, 50, 80, 90]
    assert audit.intersects([20, 50, 80, 90], [21, 51, 79, 89])
    assert not audit.intersects([20, 50, 80, 90], [80, 50, 100, 90])


def test_table_cells_and_headers_remain_distinct_from_source_column_verification():
    native = {
        "pages": {"1": {"size": {"height": 800}}},
        "texts": [],
        "tables": [
            {
                "self_ref": "#/tables/0",
                "prov": [{"page_no": 1}],
                "data": {
                    "table_cells": [
                        {
                            "text": "Private standards",
                            "col_header": True,
                            "start_col_offset_idx": 0,
                            "bbox": {
                                "l": 10,
                                "r": 100,
                                "t": 100,
                                "b": 200,
                                "coord_origin": "TOPLEFT",
                            },
                        },
                        {
                            "text": "Commercial blood pressure standard",
                            "col_header": False,
                            "start_col_offset_idx": 1,
                            "bbox": {
                                "l": 110,
                                "r": 200,
                                "t": 100,
                                "b": 200,
                                "coord_origin": "TOPLEFT",
                            },
                        },
                    ]
                },
            }
        ],
    }
    pages = audit.collect_pages(
        native, [{"audit_pdf_page": 1, "original_pdf_page": 99, "height": 800, "width": 600}]
    )
    source = {
        "source_id": "s",
        "module": "hypertension",
        "section": "2.3.1",
        "printed_page": 88,
        "pdf_page": 99,
        "bbox": [110, 100, 200, 200],
        "evidence_text": "Commercial blood pressure standard",
        "text_sha256": "pin",
    }
    result = audit.align_sources([source], pages)[0]
    assert result["region_token_coverage"] == 1
    assert result["overlapping_native_table_cell_count"] == 1
    assert result["commercial_column_and_footnote_review"] == "pending"
    assert result["overlapping_native_regions"][0]["native_cell"]["start_col_offset_idx"] == 1


def test_lexical_alignment_does_not_replace_missing_original_words():
    assert audit.token_coverage("severe severe recent hypoglycaemia", "severe recent event") == 0.5
    assert audit.normalized("full \noriginal\t text") == "full original text"

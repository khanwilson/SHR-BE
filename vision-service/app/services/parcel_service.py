import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.cv.coordinate_table_extractor import extract_from_coordinate_table, extract_from_ocr_text
from app.cv.diagram_locator import locate_diagram_region
from app.cv.edge_measurer import extract_edge_measurements
from app.cv.image_utils import decode_image, deskew_region, encode_image_base64, resize_for_processing
from app.cv.parcel_info_extractor import extract_parcel_info
from app.cv.polygon_extractor import extract_parcel_polygon

_executor = ThreadPoolExecutor(max_workers=2)


async def process_parcel_image(image_bytes: bytes, ocr_text: str = "") -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _run_pipeline, image_bytes, ocr_text)


def _run_pipeline(image_bytes: bytes, ocr_text: str = "") -> dict:
    try:
        img = decode_image(image_bytes)
        img = resize_for_processing(img)

        # Step 1: Extract parcel info fields (Section II.1 text data)
        parcel_info = extract_parcel_info(img)

        # Step 2: Always locate diagram region first
        diagram = locate_diagram_region(img)

        # Step 3: Search for coordinate table (BẢNG LIỆT KÊ TỌA ĐỘ GÓC RANH)
        # Prefer high-quality OCR text (Google Vision) over re-scanning the image
        table_result = extract_from_ocr_text(ocr_text) if ocr_text else {}
        if len(table_result.get("vertices", [])) < 3:
            table_result = extract_from_coordinate_table(diagram)
        if len(table_result.get("vertices", [])) >= 3:
            return {
                "success": True,
                "parcel_info": parcel_info.get("fields", {}),
                "vertices": table_result["vertices"],
                "edges": table_result.get("edges", []),
                "confidence": table_result["confidence"],
                "vertex_count": table_result["vertex_count"],
                "source": "coordinate_table",
                "coordinates_vn2000": table_result.get("coordinates_vn2000", []),
                "diagram_image_b64": encode_image_base64(diagram),
            }

        # Step 4: No coordinate table — fall back to polygon detection
        diagram = deskew_region(diagram)
        polygon_result = extract_parcel_polygon(diagram)

        if not polygon_result["vertices"]:
            return {
                "success": False,
                "parcel_info": parcel_info.get("fields", {}),
                "vertices": [],
                "edges": [],
                "confidence": 0.0,
                "vertex_count": 0,
                "error": "Could not detect parcel polygon (tried coordinate table and polygon detection)",
                "diagram_image_b64": encode_image_base64(diagram),
                "_table_ocr": table_result.get("_ocr_text", ""),
            }

        edges = extract_edge_measurements(diagram, polygon_result["vertices"])

        return {
            "success": True,
            "parcel_info": parcel_info.get("fields", {}),
            "vertices": polygon_result["vertices"],
            "edges": edges,
            "confidence": polygon_result["confidence"],
            "vertex_count": polygon_result["vertex_count"],
            "source": "polygon_detection",
            "diagram_image_b64": encode_image_base64(diagram),
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "parcel_info": {},
            "vertices": [],
            "edges": [],
            "confidence": 0.0,
            "vertex_count": 0,
            "error": str(exc),
        }

import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.cv.diagram_locator import locate_diagram_region
from app.cv.edge_measurer import extract_edge_measurements
from app.cv.image_utils import decode_image, deskew_region, encode_image_base64, resize_for_processing
from app.cv.polygon_extractor import extract_parcel_polygon

_executor = ThreadPoolExecutor(max_workers=2)


async def process_parcel_image(image_bytes: bytes) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _run_pipeline, image_bytes)


def _run_pipeline(image_bytes: bytes) -> dict:
    try:
        img = decode_image(image_bytes)
        img = resize_for_processing(img)

        # Step 1: Find diagram region
        diagram = locate_diagram_region(img)
        diagram = deskew_region(diagram)

        # Step 2: Extract parcel polygon
        polygon_result = extract_parcel_polygon(diagram)

        if not polygon_result["vertices"]:
            return {
                "success": False,
                "vertices": [],
                "edges": [],
                "confidence": 0.0,
                "vertex_count": 0,
                "error": "Could not detect parcel polygon",
                "diagram_image_b64": encode_image_base64(diagram),
            }

        # Step 3: Extract edge measurements
        edges = extract_edge_measurements(diagram, polygon_result["vertices"])

        return {
            "success": True,
            "vertices": polygon_result["vertices"],
            "edges": edges,
            "confidence": polygon_result["confidence"],
            "vertex_count": polygon_result["vertex_count"],
            "diagram_image_b64": encode_image_base64(diagram),
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "vertices": [],
            "edges": [],
            "confidence": 0.0,
            "vertex_count": 0,
            "error": str(exc),
        }



import cv2
import easyocr
import torch
import json
import sys, os
from pathlib import Path

from rich.progress import Progress

VIDEO_PATH = sys.argv[1]

BOTTOM_HEIGHT = 100

READ_EVERY_X_FRAMES = 15

# Load EasyOCR model (English only)
reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())

root_dir = Path(sys.argv[1])
all_files = sorted(list(root_dir.rglob("*F.MOV")))


xs_greater_than_100 = []

xs_smaller_than_100 = [[1116, 1131], [1131, 1146], [1154, 1168], [1168, 1184], [1199, 1214], [1214, 1229], [1276, 1290], [1290, 1304], [1311, 1326], [1326, 1341], [1356, 1371], [1371, 1386]]


ys = [934, 957]
frame_coords_greater_than_100 = [[round(ys[0] / 0.45), round(ys[1] / 0.45), round(x[0] / 0.45), round(x[1] / 0.45)] for x in xs_greater_than_100]
frame_coords_smaller_than_100 = [[round(ys[0] / 0.45), round(ys[1] / 0.45), round(x[0] / 0.45), round(x[1] / 0.45)] for x in xs_smaller_than_100]

splitter_greater_than_100 = [2, 10]
splitter_smaller_than_100 = [2, 9]

j = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": []}}

def dms_to_decimal(degrees: float, minutes: float, seconds: float, hemisphere: str = "W") -> float:
    """
    Convert longitude/latitude in Degrees-Minutes-Seconds (DMS) to decimal degrees.

    Args:
        degrees (float): Degree part
        minutes (float): Minute part
        seconds (float): Second part
        hemisphere (str): Optional; one of ['N','S','E','W']
                          Used to determine sign: South & West are negative.

    Returns:
        float: Decimal degree representation
    """
    decimal = degrees + minutes / 60 + seconds / 3600

    if hemisphere:
        hemisphere = hemisphere.upper()
        if hemisphere in ['S', 'W']:
            decimal *= -1

    return round(decimal, 5)






file_count = 0

with Progress(speed_estimate_period=720) as pb:
    t0 = pb.add_task(f'Total File Progress', total=len(all_files))

    for p in all_files:
        p_str = p.as_posix()

        cap = cv2.VideoCapture(p_str)
        frame_idx = 0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    
        t1 = pb.add_task(f'{p_str}', total=total_frames)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            h, w, _ = frame.shape
            result = ""

            try:
                frame_coords = frame_coords_smaller_than_100
                count = 0
                longt = 0.0
                lat = 0.0

                longt_d = ""
                longt_m = ""
                longt_s = ""

                lat_d = ""
                lat_m = ""
                lat_s = ""
                for coord in frame_coords:
                    count += 1
                    roi = frame[coord[0]:coord[1], coord[2]:coord[3]]

                    # ----- Preprocess for white text -----
                    # gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    # _, mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)  # isolate white
                    # # mask = cv2.bitwise_not(mask)  # Uncomment if white text → black background improves OCR
                    
                    # # EasyOCR expects RGB
                    # roi_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)

                    roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)

                    # Run OCR on GPU
                    results = reader.readtext(roi_rgb, detail=1, paragraph=False, allowlist="0123456789", text_threshold=0.0, low_text=0.0, link_threshold=0.0)
                    
                    for box, text, conf in results:
                        if len(text) > 1 or len(text) < 1:
                            pb.update(task_id=t1, completed=frame_idx)
                            continue
                        if count <= 2:
                            lat_d += text
                        elif count <= 4:
                            lat_m += text
                        elif count <= 6:
                            lat_s += text
                        elif count <= 8:
                            longt_d += text
                        elif count <= 10:
                            longt_m += text
                        elif count <= 12:
                            longt_s += text
                    
                
                longt = dms_to_decimal(float(longt_d), float(longt_m), float(longt_s), "W")
                lat = dms_to_decimal(float(lat_d), float(lat_m), float(lat_s), "N")
                    

                # print(f"=== Frame {frame_idx} ===")
                # print([longt, lat])
                # # for box, text, conf in results:
                # #     print(f"{text}  (conf={conf:.3f})")
                # print("------------------------")
                j["geometry"]["coordinates"].append([float(longt), float(lat)])
                frame_idx += READ_EVERY_X_FRAMES
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            except:
                pb.update(task_id=t1, completed=frame_idx)
                continue
            pb.update(task_id=t1, completed=frame_idx)
        cap.release()

        file_count += 1
        pb.remove_task(t1)
        pb.update(task_id=t0, completed=file_count)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    video_dir_name = os.path.basename(os.path.normpath(VIDEO_PATH))
    with open(f"{script_dir}/{video_dir_name}.geojson", "w") as f:
        json.dump(j, f)
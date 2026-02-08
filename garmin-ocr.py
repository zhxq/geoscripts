import cv2
import easyocr
import torch
import json
import sys

from rich.progress import Progress

VIDEO_PATH = sys.argv[1]

BOTTOM_HEIGHT = 100

READ_EVERY_X_FRAMES = 15

# Load EasyOCR model (English only)
reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())

cap = cv2.VideoCapture(VIDEO_PATH)
frame_idx = 0


test_xs = [[770, 788], [788, 807]]

xs_greater_than_100 = [[600, 619], [619, 639], [651, 671], [671, 690], [690, 708], [708, 728], [728, 748], [770, 788], [788, 807], [807, 827], [840, 860], [860, 879], [879, 898], [898, 916], [916, 936]]

xs_smaller_than_100 = [[600, 619], [619, 639], [651, 671], [671, 690], [690, 708], [708, 728], [728, 748], [770, 788], [788, 807], [821, 841], [841, 860], [860, 879], [879, 898], [898, 917]]


# xs = [[1276, 1290], [1290, 1304], [1311, 1326], [1326, 1341], [1356, 1371], [1371, 1386]]

ys = [934, 962]

test_coords = [[round(ys[0] / 0.9), round(ys[1] / 0.9), round(x[0] / 0.9), round(x[1] / 0.9)] for x in test_xs]
frame_coords_greater_than_100 = [[round(ys[0] / 0.9), round(ys[1] / 0.9), round(x[0] / 0.9), round(x[1] / 0.9)] for x in xs_greater_than_100]
frame_coords_smaller_than_100 = [[round(ys[0] / 0.9), round(ys[1] / 0.9), round(x[0] / 0.9), round(x[1] / 0.9)] for x in xs_smaller_than_100]

splitter_greater_than_100 = [2, 10]
splitter_smaller_than_100 = [2, 9]


total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

j = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": []}}


with Progress() as pb:
    t1 = pb.add_task(f'{VIDEO_PATH} Progress', total=total_frames)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        if frame_idx % READ_EVERY_X_FRAMES:
            continue
        

        h, w, _ = frame.shape
        result = ""

        try:


            test_result = ""
            for coord in test_coords:
                roi = frame[coord[0]:coord[1], coord[2]:coord[3]]
                roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)

                # Run OCR on GPU
                results = reader.readtext(roi_rgb, detail=1, paragraph=False, allowlist="0123456789", text_threshold=0.0, low_text=0.0, link_threshold=0.0)
                for box, text, conf in results:
                    # print(f"{text}  (conf={conf:.3f})")
                    test_result += text

            test_result_int = int(test_result)

            splitter = splitter_smaller_than_100
            frame_coords = frame_coords_smaller_than_100

            if test_result_int >= 10 and test_result_int <= 12:
                frame_coords = frame_coords_greater_than_100
                splitter = splitter_greater_than_100

            count = 0
            longt = "-"
            lat = ""
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
                    # print(f"{text}  (conf={conf:.3f})")
                    if count <= 7:
                        lat += text
                    else:
                        longt += text 
                
                if count in splitter and count <= 7:
                    lat += "."
                if count in splitter and count > 7:
                    longt += "."

            # print(f"=== Frame {frame_idx} ===")
            # print([float(longt), float(lat)])
            # # for box, text, conf in results:
            # #     print(f"{text}  (conf={conf:.3f})")
            # print("------------------------")
            j["geometry"]["coordinates"].append([float(longt), float(lat)])
        except:
            pb.update(task_id=t1, completed=frame_idx)
            continue
        pb.update(task_id=t1, completed=frame_idx)

    cap.release()

with open(f"{VIDEO_PATH}.json", "w") as f:
    json.dump(j, f)
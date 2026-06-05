import cv2
import numpy as np


class LaserDetector:
    def __init__(self, color_bgr, cutoff_length=10):
        self.color_bgr = np.array(color_bgr, dtype=np.uint8).reshape((1, 1, 3))
        self.cutoff_length = cutoff_length

    def mask(self, image, s_min=50, v_min=50):
        if image is None:
            return None

        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

        hsv_color = cv2.cvtColor(self.color_bgr, cv2.COLOR_BGR2HSV)
        hue = int(hsv_color[0, 0, 0])
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        low_h = (hue - self.cutoff_length) % 180
        high_h = (hue + self.cutoff_length) % 180

        if low_h <= high_h:
            lower = np.array([low_h, s_min, v_min], dtype=np.uint8)
            upper = np.array([high_h, 255, 255], dtype=np.uint8)
            return cv2.inRange(hsv_image, lower, upper)

        lower1 = np.array([0, s_min, v_min], dtype=np.uint8)
        upper1 = np.array([high_h, 255, 255], dtype=np.uint8)
        lower2 = np.array([low_h, s_min, v_min], dtype=np.uint8)
        upper2 = np.array([179, 255, 255], dtype=np.uint8)
        return cv2.inRange(hsv_image, lower1, upper1) | cv2.inRange(hsv_image, lower2, upper2)

    def detect(self, image, contour_selection=0, s_min=50, v_min=50):
        mask = self.mask(image, s_min=s_min, v_min=v_min)
        if mask is None:
            return None

        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        contours = [contour for contour in contours if len(contour) >= 5]

        if len(contours) <= contour_selection:
            return {
                "found": False,
                "message": "No suitable contours found",
                "mask": mask,
                "annotated_image": image.copy(),
            }

        contour = contours[contour_selection]
        ellipse = cv2.fitEllipse(contour)
        annotated = image.copy()
        cv2.drawContours(annotated, contours, -1, (255, 0, 0), 1)
        cv2.ellipse(annotated, ellipse, (0, 255, 0), 2)

        center, axes, angle = ellipse
        return {
            "found": True,
            "message": "Laser detected",
            "mask": mask,
            "annotated_image": annotated,
            "ellipse": ellipse,
            "center": center,
            "axes": axes,
            "angle": angle,
            "contour_count": len(contours),
        }


def detect_red_green_lasers(image, contour_selection=0, s_min=50, v_min=50):
    red_detector = LaserDetector((0, 0, 255))
    green_detector = LaserDetector((0, 255, 0))
    red = red_detector.detect(image, contour_selection=contour_selection, s_min=s_min, v_min=v_min)
    green = green_detector.detect(image, contour_selection=contour_selection, s_min=s_min, v_min=v_min)

    distance_px = None
    annotated = image.copy() if image is not None else None

    if red and red.get("found"):
        annotated = red["annotated_image"]
    if green and green.get("found") and annotated is not None:
        cv2.ellipse(annotated, green["ellipse"], (0, 255, 0), 2)

    if red and green and red.get("found") and green.get("found"):
        red_center = np.array(red["center"])
        green_center = np.array(green["center"])
        distance_px = float(np.linalg.norm(red_center - green_center))

    return {
        "red": red,
        "green": green,
        "distance_px": distance_px,
        "annotated_image": annotated,
    }

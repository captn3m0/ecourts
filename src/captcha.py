import cv2
import numpy as np
import os
import sys
import os
import sys
import subprocess
import tempfile


class CaptchaError(Exception):
    pass


class Captcha:
    THRESHOLD = 0.4
    MAX_PIXEL_VALUE = 255
    URL = (
        "https://hcservices.ecourts.gov.in/ecourtindiaHC/securimage/securimage_show.php"
    )
    SUFFIX = ".png"

    def __init__(self, session = None):
        self.session = session

    def solve(self, retry=3):
        assert self.session is not None
        while retry > 0:
            captcha = self.session.get(self.URL)

            captcha.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=self.SUFFIX, delete=False) as f:
                f.write(captcha.content)
                f.close()
                try:
                    return self.decaptcha(f.name)
                except CaptchaError:
                    if retry > 0:
                        retry -= 1
                    else:
                        raise CaptchaError("Couldn't solve captcha after retries")

    def decaptcha(self, file):
        if not os.path.exists(file):
            raise FileNotFoundError(file)

        src = cv2.imread(file)
        threshold = int(self.MAX_PIXEL_VALUE * self.THRESHOLD)

        _, threshold_img = cv2.threshold(
            src, threshold, self.MAX_PIXEL_VALUE, cv2.THRESH_BINARY
        )

        # Create a binary mask for lines
        lines_color = np.array([0x70, 0x70, 0x70], dtype=np.uint8)
        binary_mask = cv2.inRange(src, lines_color, lines_color)

        # Apply mask to the image
        masked = cv2.bitwise_and(src, src, mask=binary_mask)

        # Dilate lines to compensate for potential masking issues
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        masked = cv2.dilate(masked, kernel)

        # Convert to grayscale
        masked_gray = cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)

        # Inpaint large lines
        dst = cv2.inpaint(threshold_img, masked_gray, 7, cv2.INPAINT_NS)

        # Dilate small lines
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dst = cv2.dilate(dst, kernel)

        # Gaussian blur
        dst = cv2.GaussianBlur(dst, (5, 5), 0)

        # Bilateral filter
        dst = cv2.bilateralFilter(dst, 5, 75, 75)

        # Convert to grayscale and apply Otsu thresholding
        dst = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
        _, dst = cv2.threshold(dst, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        dst = dst[15:65, 27:190]  # crop the image
        output_path = tempfile.mkstemp(suffix=".png")[1]
        cv2.imwrite(output_path, dst)

        process = subprocess.Popen(
            [
                "tesseract",
                output_path,
                "stdout",
                "--oem",
                "1",
                "--psm",
                "8",
                "-c",
                "tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz0123456789",
            ],
            stdout=subprocess.PIPE,
        )
        process.wait()
        output, _ = process.communicate()
        result = output.decode("utf-8").strip()
        if len(result) == 5:
            os.remove(output_path)
            return result
        else:
            raise CaptchaError("Couldn't solve captcha")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        decaptcha(sys.argv[1])
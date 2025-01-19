import cv2

_detectShadows = False
_varThreshold = 25
_history = 300
_thresh = 200
_maxvalue = 255
_kernel = None
_countourThreshold = 1000

foog = cv2.createBackgroundSubtractorMOG2(detectShadows=_detectShadows, varThreshold=_varThreshold, history=_history) 

def get_motions(frames):
    results = dict(zip(frames.values(), len(frames) * [False]))
    for url, frame in frames.items():
        fgmask = foog.apply(frame)
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, _kernel) # cv2.MORPH_OPEN
        fgmask = cv2.threshold(fgmask, _thresh, _maxvalue, cv2.THRESH_BINARY)[1]
        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            cnt = max(contours, key=cv2.contourArea)
            if cv2.contourArea(cnt) > _countourThreshold:
                results[url] = True
                print('Motion Detected')
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
    return results



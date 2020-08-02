from src.gui_tool.utils import get_ord, RotatingLog
import numpy as np
import cv2
from .VideoTaggingContext import VideoTaggingContext
from .BoundingBoxManager import BoundingBoxManager
from .additional_tags import AdditionalTagWindow
from .id_input_popup import PopUpWindow
from .label_popup import LabelPopup
from enum import Enum, auto
import cv2
from .ManualTaggingAbortedException import ManualTaggingAbortedException

GENERAL_INSTRUCTIONS = [
    ["tab", "Switch mode"],
    ["h", "Open instructions page"],
    ["a", "1 back"],
    ["s", "10 back"],
    ["d", "1 forward"],
    ["w", "10 forward"],
    ["Space", "Pause/unpause"],
    ["Enter", "Finish and continue"],
    ["Esc", "Abort and restart tagging. Will raise ManualTaggingAbortedException"],
    ["t", "Opens window for user customizable tags"],
]
BBOX_MODE_INSTRUCTIONS = [
    ["click & drag", "Create bounding box range for commands"],
    ["i",
        "Select a new integer ID to work on, as well as its class",
        "If ID already exists, will select original",
        "If ID already exists, the class for the original will not be replaced until u is pressed"],
    ["r", "Reset current task"],
    ["c", "Clear existing bounding boxes over frames", "Press after clicking on 2 frames"],
    # ["v", "Re-interpolate over frames [NOT implemented]"],
    ["b", "Define bounding boxes over range", "Press after selecting 2 bounding boxes"],
    ["u", "Update class of current id based on popup input"],
    ["p", "Remove all unused bounding box ids (ids without any bounding boxes)"],
]
SELECTION_MODE_INSTRUCTIONS = [
    ["mouse click", "Select bounding box"],
    ["n",
        "Toggle whether it is a dashcam video",
        "NOTE: by default, all videos will be dashcam",
        "Pressing n the first time will mark the video as not dashcam"],
]

class VideoPlayerGUIManager(object):
    PROGRESS_BAR_NAME = "progress"
    FRAME_RATE_BAR_NAME = "frame_delay"
    PAUSE_BUTTON_NAME = "pause"
    WINDOW_NAME = 'tagger'

    LOG_LINES = 5
    LOG_LINE_HEIGHT = 17
    LOG_LINE_MARGIN = 2
    LOG_START_X = 250
    IMG_STARTING_Y = LOG_LINE_HEIGHT * LOG_LINES + LOG_LINE_MARGIN * (LOG_LINES + 1) + 3

    def __init__(self, context: VideoTaggingContext):
        self.context = context
        self.vcm = self.context.vcm
        self.frame_rate = 25
        self.logger = RotatingLog(self.LOG_LINES)
        self.ignore_index_change_interval = self.vcm.get_frames_count() // 50

        self.bbm = BoundingBoxManager()
        if context.bbox_fields is not None:
            self.bbm.set_to(*context.bbox_fields)

        self.mode_handlers = [
            InternaSelectionMode(self),
            InternalBBoxMode(self)
        ]
        self.mode_handler_i = 0

        self.instructions = GENERAL_INSTRUCTIONS

    def start(self):
        self.set_GUI()
        try:
            self.logger.log("Starting with: {0} bounding box ids".format(self.bbm.get_n_ids()))
            self.play_video()
        except ManualTaggingAbortedException:
            raise
        finally:
            self.cleanup()

        self.context.bbox_fields = self.bbm.extract()
        assert(len(set([len(f) for f in self.context.bbox_fields])) == 1)

    def set_GUI(self):
        cv2.namedWindow(self.WINDOW_NAME)
        cv2.setMouseCallback(self.WINDOW_NAME,
             lambda event, x, y, flags, param: self.handleClick(event, x, y, flags, param))

        def set_frame_rate_callback(value):
            self.frame_rate = max(1, value)
        def set_progress_rate_callback(value):
            if abs(value - self.vcm.get_frame_index()) <= self.ignore_index_change_interval:
                return
            self.vcm.start_from(value)
        def set_paused_callback(value):
            if self.vcm is not None:
                self.vcm.set_paused(value)

        cv2.createTrackbar(self.PROGRESS_BAR_NAME, self.WINDOW_NAME, 0, max(0, self.vcm.get_frames_count()-1),
                           set_progress_rate_callback)
        cv2.createTrackbar(self.FRAME_RATE_BAR_NAME, self.WINDOW_NAME,
                           self.frame_rate, 200, set_frame_rate_callback)
        cv2.createTrackbar(self.PAUSE_BUTTON_NAME,  self.WINDOW_NAME,
                           False, 1, set_paused_callback)

    def play_video(self):
        shown_for_first_time = False
        while True:
            if shown_for_first_time and cv2.getWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_VISIBLE) <= 0:  # Window closed. Abort
                raise ManualTaggingAbortedException("Tagging operation aborted by closing window")

            frame = self.vcm.next().copy()
            frame_index = self.vcm.get_frame_index()
            frame = self.bbm.modify_frame(frame, frame_index)
            frame = self.get_mode_handler().modify_frame(frame, frame_index)
            cv2.imshow(self.WINDOW_NAME, self.build_frame(frame))
            shown_for_first_time = True

            cv2.setTrackbarPos(self.PROGRESS_BAR_NAME, self.WINDOW_NAME, frame_index)

            received_key = cv2.waitKey(self.frame_rate) & 0xFF
            if received_key == get_ord("esc"):  # Escape key
                raise ManualTaggingAbortedException("Tagging operation aborted")
            elif received_key == get_ord("enter"):  # Enter
                break
            elif received_key == ord("t"):
                window = AdditionalTagWindow()
                tags = window.get_user_tags()
                self.context.set_additional_tags(tags)
            elif received_key == ord("h"):
                window = LabelPopup(
                    "GUI controls reference",
                    self.instructions + [["", ""]] + self.get_mode_handler().instructions
                )
                window.run()
            elif received_key == get_ord("a"):
                self.vcm.shift_frame_index(-1)
            elif received_key == get_ord("s"):
                self.vcm.shift_frame_index(-10)
            elif received_key == get_ord("d"):
                self.vcm.shift_frame_index(1)
            elif received_key == get_ord("w"):
                self.vcm.shift_frame_index(10)
            elif received_key == get_ord(" "):
                cv2.setTrackbarPos(self.PAUSE_BUTTON_NAME, self.WINDOW_NAME, 0 if self.vcm.get_paused() else 1)

            if received_key == get_ord("tab"):
                self.mode_handler_i += 1
                self.mode_handler_i %= len(self.mode_handlers)
                self.logger.log("Changed mode")
            else:
                self.get_mode_handler().handle_keyboard(received_key)

    def build_frame(self, frame):
        img = np.zeros((
            self.context.file_height + self.IMG_STARTING_Y,
            self.context.file_width,
            3), np.uint8)

        def write_top_text():
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            font_color = (255, 255, 255)
            for i, msg in enumerate(self.logger.get_logs()):
                starting_index = (self.LOG_START_X, self.LOG_LINE_HEIGHT * (i+1) + self.LOG_LINE_MARGIN * i)
                cv2.putText(img, msg, starting_index,
                            font, font_scale, font_color)

            for i, msg in enumerate(self.get_mode_handler().get_state_message()):
                starting_index = (0, self.LOG_LINE_HEIGHT * (i + 1) + self.LOG_LINE_MARGIN * i)
                cv2.putText(img, msg, starting_index,
                            font, font_scale, font_color)

        write_top_text()
        displayed = cv2.cvtColor(frame, cv2.IMREAD_COLOR)
        img[self.IMG_STARTING_Y:, 0:] = displayed
        return img

    def handleClick(self, event, x, y, flags, param):
        y = y-self.IMG_STARTING_Y
        self.get_mode_handler().handle_click(event, x, y, flags, param)

    def get_mode_handler(self):
        return self.mode_handlers[self.mode_handler_i]

    def cleanup(self):
        self.vcm.release()
        cv2.destroyAllWindows()

class InternalMode(object):
    def __init__(self, parent: VideoPlayerGUIManager, instructions: list):
        self.par = parent
        self.instructions = instructions
    def handle_click(self, event, x, y, flags, param):
        raise NotImplementedError()
    def handle_keyboard(self, received_key: int):
        raise NotImplementedError()
    def get_state_message(self):
        raise NotImplementedError()
    def modify_frame(self, frame, i):
        return frame
    def log(self, msg):
        self.par.logger.log(msg)

class InternaSelectionMode(InternalMode):
    def __init__(self, parent: VideoPlayerGUIManager):
        super().__init__(parent, SELECTION_MODE_INSTRUCTIONS)
    def handle_click(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.par.bbm.handleClickSelection(self.par.vcm.get_frame_index(), x, y)
    def handle_keyboard(self, received_key: int):
        par = self.par
        if received_key == get_ord("n"):
            par.context.mark_is_dashcam(not par.context.is_dashcam)
            par.logger.log("Marked video as {0}".format("dashcam" if par.context.bbox_fields else "not dishcam"))
    def get_state_message(self):
        return [
            "Selection Mode",
            "{0} Selected".format(self.par.bbm.get_n_selected()),
            "{0} Total".format(self.par.bbm.get_n_ids()),
        ]

class InternalBBoxMode(InternalMode):
    BOX_DRAWING_DISPLAY = {
        "color": (150, 255, 150),
        "lineType": 2,
        "thickness": 2
    }

    def __init__(self, parent: VideoPlayerGUIManager):
        super().__init__(parent, BBOX_MODE_INSTRUCTIONS)
        self.mouse_position = None
        self.selected_locations = []
        self.curr_ref_point = []
        self.selected_id = 1
        self.selected_cls = ""

    def handle_click(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.curr_ref_point = [(x, y)]
        elif event == cv2.EVENT_MOUSEMOVE:
            self.mouse_position = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            if len(self.curr_ref_point) == 1:
                curr_frame = self.par.vcm.get_frame_index()
                self.curr_ref_point.append((x, y))
                self.log("Manually Selected bounding box {0} on frame {1}".format(
                    self.curr_ref_point, curr_frame))

                self.selected_locations.append([
                    curr_frame,
                    self.curr_ref_point
                ])
                if len(self.selected_locations) > 2:
                    self.selected_locations = self.selected_locations[-2:]
                if len(self.selected_locations) == 2:
                    if self.selected_locations[0][0] > self.selected_locations[1][0]:
                        self.selected_locations = [self.selected_locations[1], self.selected_locations[0]]
                    self.log("Use keyboard controls to manipulate BBox {0} from frames {1} to {2}".format(
                        self.selected_id,
                        self.selected_locations[0][0],
                        self.selected_locations[1][0]))

    def handle_keyboard(self, received_key: int):
        par = self.par
        bbm = self.par.bbm
        if received_key == get_ord("i"):  # Select id
            id, cls = PopUpWindow().run()
            if id is None or id == "":
                self.log("Select ID operation canceled. Still on {0}".format(self.selected_id))
            else:
                try:
                    id = int(id)
                    self.log("Switched id from {0} to {1}".format(self.selected_id, id))
                    self.selected_id = id
                    self.selected_cls = cls

                    if bbm.has_id(id) and bbm.get_cls(id) != self.selected_cls:
                        self.log("WARN: class input for existing id {0} ({1}) differ from current ({2})".format(
                            id, self.selected_cls, bbm.get_cls(id)))
                        self.log("Press u to replace")
                except:
                    self.log("Input ID not valid. Still on {0}".format(self.selected_id))
        elif received_key == get_ord("r"):
            self.reset_task()
            self.log("Selected bounding boxes reset".format(self.selected_id))
        elif received_key == get_ord("b"):
            if len(self.selected_locations) == 2:
                if not bbm.has_id(self.selected_id):
                    bbm.add_or_update_id(self.selected_id, self.selected_cls)
                    self.log("New id {0} for class {1} added".format(self.selected_id, self.selected_cls))
                bbm.replace_in_range(
                    self.selected_id,
                    self.selected_locations[0][0],
                    self.selected_locations[0][1],
                    self.selected_locations[1][0],
                    self.selected_locations[1][1])
                self.log("Bounding box for ID {0} set over index range [{1}, {2}]".format(
                    self.selected_id, self.selected_locations[0][0], self.selected_locations[1][0]))
            else:
                self.log("Not enough inputs. Command ignored. Please draw 2 bounding boxes")
        elif received_key == get_ord("c"):
            if len(self.selected_locations) == 2 and bbm.has_id(self.selected_id):
                i1 = self.selected_locations[0][0]
                i2 = self.selected_locations[1][0]
                bbm.clear_in_range(self.selected_id, i1, i2)
                self.log("Bbox for ID {0} cleared over index range [{1}, {2}]".format(self.selected_id, i1, i2))

                unused_ids = bbm.get_unused_ids()
                if len(unused_ids) > 0:
                    self.log("WARN: Exists ids without bounding box: {0}".format(list(unused_ids)))
                    self.log("Press p to remove")
            elif not len(self.selected_locations) == 2:
                self.log("Not enough inputs. Command ignored. Please click on 2 frames")
            elif bbm.has_id(self.selected_id):
                self.log("Cannot clear bboxes - ID {0} does not exist".format(self.selected_id))
        elif received_key == get_ord("p"):
            deleted_ids = bbm.remove_unused_ids()
            self.log("Remove {0} ids without bounding boxes: {1}".format(len(deleted_ids), list(deleted_ids)))
        elif received_key == get_ord("u"):
            if not bbm.has_id(self.selected_id):
                self.log("ID {0} does not exist".format(self.selected_id))
            else:
                prev = bbm.get_cls(self.selected_id)
                bbm.add_or_update_id(self.selected_id, self.selected_cls)
                self.log("Class for ID {0} updated from {1} to {2}".format(
                    self.selected_id, prev, self.selected_cls))

    def reset_task(self):
        self.selected_locations = []
        self.curr_ref_point = []

    def modify_frame(self, frame, i):
        if len(self.curr_ref_point) == 1:
            cv2.rectangle(frame, self.curr_ref_point[0], self.mouse_position, **self.BOX_DRAWING_DISPLAY)
        return frame

    def get_state_message(self):
        bbm = self.par.bbm
        selected_msg = ""
        if len(self.selected_locations) == 0:
            selected_msg = "No Input"
        elif len(self.selected_locations) == 1:
            selected_msg = "Input: From {0}".format(self.selected_locations[0][0])
        elif len(self.selected_locations) == 2:
            selected_msg = "Input: {0} to {1}".format(self.selected_locations[0][0], self.selected_locations[1][0])
        else:
            raise Exception("Invalid state")
        messages = [
            "BBox Mode:",
            "{0} BBoxes total".format(bbm.get_n_ids()),
            "Target: {0} id {1} [{2}]".format(
                "existing" if bbm.has_id(self.selected_id) else "new",
                self.selected_id,
                bbm.get_cls(self.selected_id) if bbm.has_id(self.selected_id) else self.selected_cls
            ),
            selected_msg
        ]
        if len(self.curr_ref_point) == 1:
            messages.append("Drawing from {0}".format(str(self.curr_ref_point[0])))
        return messages


from __future__ import annotations
from .const_http_cmd import YiHttpCmdId
from .const_http_cmd_rc_params import *
from .const_http_enum_extra import *
from typing import Dict, List

class YiHttpCmd():
    @staticmethod
    def from_json(json : str) -> YiHttpCmd:
        raise NotImplementedError
    
    def to_json(self) -> Dict[str,str]:
        raise NotImplementedError

class CmdFileList(YiHttpCmd):
    def __init__(self, permit_raw: bool = False, permit_jpg: bool = False):
        super().__init__()
        self.permit_raw = permit_raw
        self.permit_jpg = permit_jpg

    def to_json(self) -> Dict[str, str]:
        filetype = "all"
        if self.permit_raw and not self.permit_jpg:
            filetype = "DNG"
        elif not self.permit_raw and self.permit_jpg:
            filetype = "JPG"
        
        return {
            "command": "GetFileList",
            "range_start": "0",
            "range_end": "999",  # Assuming 999 is a large enough number to get all files
            "filetype": filetype
        }

class CmdFileDelete(YiHttpCmd):
    def __init__(self, photo_paths : List[str]):
        super().__init__()
        self.__paths = photo_paths
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_FILE_DELETE.value, "file_list":self.__paths}
    
class CmdGetCameraStatus(YiHttpCmd):
    def __init__(self):
        super().__init__()

    def to_json(self) -> Dict[str, str]:
        return {"command": "GetCameraStatus"}

class CmdFileGet(YiHttpCmd):
    def __init__(self, path_file: str):
        super().__init__()
        self.__path = path_file
    
    def to_json(self) -> Dict[str, str]:
        return {
            "command": "GetFile",
            "path": self.__path,
            "date": "",
            "resulotion": "Original"  # Note the correct spelling might be "resolution", adjust if needed
        }

class CmdFileGetMidThumb(YiHttpCmd):
    def __init__(self, path_file: str):
        super().__init__()
        self.__path = path_file
    
    def to_json(self) -> Dict[str, str]:
        return {
            "command": "GetFile",
            "path": self.__path,
            "date": "",
            "resulotion": "MidThumb"  # Note the correct spelling might be "resolution", adjust if needed
        }

class CmdFileGetThumbnail(YiHttpCmd):
    def __init__(self, path_file: str):
        super().__init__()
        self.__path = path_file
    
    def to_json(self) -> Dict[str, str]:
        return {
            "command": "GetFile",
            "path": self.__path,
            "date": "",
            "resulotion": "Thumbnail"  # Note the correct spelling might be "resolution", adjust if needed
        }

class CmdLiveViewStart(YiHttpCmd):
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_LIVE_VIEW_START.value}

class RcCmdSetCameraMode(YiHttpCmd):
    def __init__(self, mode : RcExposureMode):
        """Change camera mode.

        Args:
            mode (RcExposureMode): New mode dial setting.
        """
        super().__init__()
        self.__mode = mode

    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_EXPOSURE_MODE.value, "DialMode":self.__mode.value}

class RcCmdSetMeteringMode(YiHttpCmd):
    def __init__(self, mode : RcMeteringMode):
        super().__init__()
        self.__mode = mode
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_METERING_MODE.value, "MeteringMode":self.__mode.value}

class RcCmdSetFocusingMode(YiHttpCmd):
    def __init__(self, mode : RcFocusMode):
        super().__init__()
        self.__mode = mode
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_FOCUS_MODE.value, "FocusMode":self.__mode.value}

class RcCmdSetImageQuality(YiHttpCmd):
    def __init__(self, quality : RcImageQuality):
        super().__init__()
        self.__quality = quality
    
    def to_json(self) -> Dict[str,str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_IMAGE_QUALITY.value, "ImageQuality":self.__quality.value}

class RcCmdSetImageAspect(YiHttpCmd):
    def __init__(self, aspect : RcImageAspect):
        super().__init__()
        self.__aspect = aspect
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_IMAGE_ASPECT.value, "ImageAspect":self.__aspect.value}

class RcCmdSetImageFormat(YiHttpCmd):
    def __init__(self, file_format : RcFileFormat):
        super().__init__()
        self.__file_format = file_format
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_IMAGE_FORMAT.value, "FileFormat":self.__file_format.value}

class RcCmdSetDriveMode(YiHttpCmd):
    def __init__(self, drive_mode : RcDriveMode):
        super().__init__()
        self.__drive_mode = drive_mode
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_DRIVE_MODE.value, "DriveMode":self.__drive_mode.value}

class RcCmdSetFStop(YiHttpCmd):
    def __init__(self, f_stop : RcFStop):
        super().__init__()
        self.__f_stop = f_stop
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_FNUMBER.value, "Fnumber":self.__f_stop.value}

class RcCmdSetShutterSpeed(YiHttpCmd):
    def __init__(self, shutter_speed : RcShutterSpeed):
        super().__init__()
        self.__shutter_speed = shutter_speed
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_SHUTTER_SPEED.value, "ShutterSpeed":self.__shutter_speed.value}

class RcCmdSetExposureValueOffset(YiHttpCmd):
    def __init__(self, ev_offset : RcEvOffset):
        super().__init__()
        self.__ev_offset = ev_offset
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_EV.value, "EV":self.__ev_offset.value}

class RcCmdSetColorStyle(YiHttpCmd):
    def __init__(self, tone : RcColorStyle):
        super().__init__()
        self.__style = tone
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_COLOR_MODE.value, "ColorMode":self.__style.value}

class RcCmdSetWhiteBalanceMode(YiHttpCmd):
    def __init__(self, wb : RcWhiteBalance):
        super().__init__()
        self.__balance = wb
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_WB.value, "WB":self.__balance.value}

class RcCmdSetIso(YiHttpCmd):
    def __init__(self, iso : RcIso):
        super().__init__()
        self.__iso = iso
    
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SET_ISO.value, "ISO":self.__iso.value}

class RcCmdShootPhoto(YiHttpCmd):
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_SHOOT.value}

class RcCmdStart(YiHttpCmd):
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_START.value}

class RcCmdStop(YiHttpCmd):
    def to_json(self) -> Dict[str, str]:
        return {"command":YiHttpCmdId.CMD_RC_STOP.value}
    
class RcCmdGetCameraConfig(YiHttpCmd):
    def to_json(self) -> Dict[str, str]:
        return {"command": YiHttpCmdId.CMD_RC_GET_CAMERA_CONFIG.value}

class RcCmdFocus(YiHttpCmd):
    def to_json(self) -> Dict[str, str]:
        return {"command": YiHttpCmdId.CMD_RC_FOCUS.value}

class RcCmdAdjustMF(YiHttpCmd):
    def __init__(self, adjustment_value: int):
        super().__init__()
        self.__adjustment_value = adjustment_value

    def to_json(self) -> Dict[str, str]:
        return {"command": YiHttpCmdId.CMD_RC_ADJUST_MF.value, "adjustment_value": str(self.__adjustment_value)}

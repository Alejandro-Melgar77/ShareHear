import logging
from typing import List, Optional, Tuple
import ctypes
from ctypes import wintypes
import comtypes
import comtypes.client
from comtypes import GUID, COMMETHOD, IUnknown, HRESULT
from pycaw.pycaw import AudioUtilities

logger = logging.getLogger(__name__)

CLSID_PolicyConfigClient = GUID('{870af99c-171d-4f9e-af0d-e63df40c2bc9}')

class IPolicyConfig(IUnknown):
    _iid_ = GUID('{f8679f50-850a-41cf-9c72-430f290290c8}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetMixFormat',
                  (['in'], ctypes.c_wchar_p, 'pwstrDeviceId'),
                  (['out'], ctypes.c_void_p, 'pWaveFormatEx')),
        COMMETHOD([], HRESULT, 'GetDeviceFormat'),
        COMMETHOD([], HRESULT, 'ResetDeviceFormat'),
        COMMETHOD([], HRESULT, 'SetDeviceFormat'),
        COMMETHOD([], HRESULT, 'GetProcessingPeriod'),
        COMMETHOD([], HRESULT, 'SetProcessingPeriod'),
        COMMETHOD([], HRESULT, 'GetShareMode'),
        COMMETHOD([], HRESULT, 'SetShareMode'),
        COMMETHOD([], HRESULT, 'GetPropertyValue'),
        COMMETHOD([], HRESULT, 'SetPropertyValue'),
        COMMETHOD([], HRESULT, 'SetDefaultEndpoint',
                  (['in'], ctypes.c_wchar_p, 'pwstrDeviceId'),
                  (['in'], wintypes.DWORD, 'Role')),
        COMMETHOD([], HRESULT, 'SetEndpointVisibility')
    ]


class WindowsAudioRouter:
    """
    Manages Windows default audio routing so ShareHear behaves exactly
    like connecting physical Bluetooth headphones:
    - When streaming starts: switches Windows default output to the silent/virtual channel,
      automatically muting physical desk speakers.
    - When streaming stops: restores Windows default output back to physical speakers.
    """

    def __init__(self) -> None:
        self._previous_device_id: Optional[str] = None
        self._is_diverted = False

    @staticmethod
    def get_current_default() -> Optional[Tuple[str, str]]:
        """Returns (friendly_name, device_id) of the current default playback device."""
        try:
            sp = AudioUtilities.GetSpeakers()
            if sp:
                return (sp.FriendlyName or "Altavoces", sp.id)
        except Exception as e:
            logger.debug("Error getting default speakers: %s", e)
        return None

    @staticmethod
    def set_default_device(device_id: str) -> bool:
        """Sets the Windows default audio endpoint for Console, Multimedia, and Communications."""
        try:
            policy = comtypes.client.CreateObject(CLSID_PolicyConfigClient, interface=IPolicyConfig)
            # Role 0: eConsole (Games/System), Role 1: eMultimedia (Music/Movies), Role 2: eCommunications (Calls)
            for role in (0, 1, 2):
                policy.SetDefaultEndpoint(device_id, role)
            logger.info("Windows default audio endpoint set to %s", device_id)
            return True
        except Exception as e:
            logger.error("Failed to set default endpoint to %s: %s", device_id, e)
            return False

    @staticmethod
    def find_silent_target_device() -> Optional[Tuple[str, str]]:
        """
        Finds the best target device to route audio to (so physical speakers stay silent).
        Prioritizes:
        1. VB-CABLE ('cable')
        2. High Definition Audio motherboard jack ('high definition')
        """
        try:
            devices = AudioUtilities.GetAllDevices()
            cable_dev = None
            hda_dev = None

            for d in devices:
                if d.state.name != 'Active':
                    continue
                # Only output / render endpoints
                if not d.id.startswith('{0.0.0.'):
                    continue

                name_lower = (d.FriendlyName or '').lower()
                if 'cable' in name_lower:
                    cable_dev = (d.FriendlyName, d.id)
                elif 'high definition' in name_lower and hda_dev is None:
                    hda_dev = (d.FriendlyName, d.id)

            if cable_dev:
                return cable_dev
            if hda_dev:
                return hda_dev

        except Exception as e:
            logger.debug("Error finding silent target: %s", e)

        return None

    def route_to_sharehear(self) -> Optional[str]:
        """
        Diverts Windows audio to the silent channel.
        Remembers previous speaker to restore later.
        Returns the friendly name of the activated target device, or None if failed.
        """
        if self._is_diverted:
            return None

        current = self.get_current_default()
        target = self.find_silent_target_device()

        if not target:
            logger.warning("No silent target device found to route audio to.")
            return None

        target_name, target_id = target

        # Remember previous device if it's different from the target
        if current and current[1] != target_id:
            self._previous_device_id = current[1]
            logger.info("Saved previous audio output: %s (%s)", current[0], current[1])
        else:
            self._previous_device_id = None

        if current and current[1] == target_id:
            # Already on target
            self._is_diverted = True
            return target_name

        if self.set_default_device(target_id):
            self._is_diverted = True
            logger.info("Auto-switched Windows audio output to %s (physical speakers silenced)", target_name)
            return target_name

        return None

    def restore_original_device(self) -> bool:
        """Restores Windows audio output back to the physical speakers."""
        if not self._is_diverted:
            return False

        self._is_diverted = False

        if self._previous_device_id:
            logger.info("Restoring previous audio output: %s", self._previous_device_id)
            success = self.set_default_device(self._previous_device_id)
            self._previous_device_id = None
            return success
        else:
            # If no previous device was recorded, find physical USB speaker if present
            try:
                for d in AudioUtilities.GetAllDevices():
                    if d.state.name == 'Active' and d.id.startswith('{0.0.0.'):
                        if 'usb speaker' in (d.FriendlyName or '').lower():
                            self.set_default_device(d.id)
                            logger.info("Restored output to USB Speaker: %s", d.FriendlyName)
                            return True
            except Exception:
                pass
        return False

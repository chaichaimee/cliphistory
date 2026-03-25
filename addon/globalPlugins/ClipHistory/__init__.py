# __init__.py
# Copyright (C) 2026 Chai Chaimee
# Licensed under GNU General Public License. See COPYING.txt for details.

import addonHandler
import globalPluginHandler
import wx
import gui
import ui
import api
import core
import scriptHandler
import time
import logging

from . import clipboard_utils
from .clip import ClipHistoryManager

addonHandler.initTranslation()
log = logging.getLogger(__name__)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = "ClipHistory"

	def __init__(self):
		super().__init__()
		try:
			self.manager = ClipHistoryManager()
			self.timer = wx.Timer()
			self.timer.Bind(wx.EVT_TIMER, self.on_clipboard_check)
			self.timer.Start(500)
			self.last_clipboard_text = ""
			self.dialog = None

			# Multi‑tap handling
			self._tap_count = 0
			self._last_tap_time = 0
			self._tap_timer = None
			self._tap_threshold = 0.5

			log.info("ClipHistory plugin initialized")
		except Exception as e:
			log.error(f"ClipHistory initialization failed: {e}", exc_info=True)

	def terminate(self):
		if self.timer.IsRunning():
			self.timer.Stop()
		if self.dialog:
			self.dialog.Destroy()
		if hasattr(self, 'manager'):
			self.manager.save()
		log.info("ClipHistory plugin terminated")

	def on_clipboard_check(self, event):
		try:
			data = clipboard_utils.get_clipboard_data()
			if data and data.get('text') and data['text'] != self.last_clipboard_text:
				self.manager.add_item(data)
				self.last_clipboard_text = data['text']
				log.info(f"New clipboard item captured: {data['text'][:50]}")
				if self.dialog and self.dialog.IsShown():
					wx.CallAfter(self.dialog.update_list)
		except Exception as e:
			log.warning(f"Clipboard check error: {e}")

	def _execute_tap_action(self):
		log.debug(f"_execute_tap_action called with count: {self._tap_count}")
		try:
			if self._tap_count == 1:
				self.show_dialog()
			elif self._tap_count >= 2:
				self.manager.clear_non_pinned()
				ui.message(_("Cleared all"))
				if self.dialog and self.dialog.IsShown():
					wx.CallAfter(self.dialog.update_list)
		except Exception as e:
			log.error(f"Error in tap action: {e}")
		finally:
			self._tap_count = 0

	@scriptHandler.script(gesture="kb:windows+v", description=_("Opens clip history (single) clears all (double)"))
	def script_openClipHistory(self, gesture):
		current_time = time.time()
		if current_time - self._last_tap_time > self._tap_threshold:
			self._tap_count = 0
			if self._tap_timer and self._tap_timer.IsRunning():
				self._tap_timer.Stop()
		self._tap_count += 1
		self._last_tap_time = current_time
		if self._tap_timer and self._tap_timer.IsRunning():
			self._tap_timer.Stop()
		self._tap_timer = wx.CallLater(int(self._tap_threshold * 1000), self._execute_tap_action)

	def show_dialog(self):
		if self.dialog and self.dialog.IsShown():
			self.dialog.Raise()
			return
		from .clip import ClipHistoryDialog
		self.dialog = ClipHistoryDialog(gui.mainFrame, self.manager)
		gui.mainFrame.prePopup()
		self.dialog.Show()
		self.dialog.CentreOnScreen()
		self.dialog.Raise()
		gui.mainFrame.postPopup()
		log.info("Dialog shown")
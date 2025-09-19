# --------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2025 Martin Jan Köhler
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-or-later
#--------------------------------------------------------------------------------

from __future__ import annotations
from dataclasses import dataclass
import os 
from pathlib import Path
import sys
import traceback
from typing import *

import pya

from klayout_plugin_utils.debugging import debug, Debugging
from klayout_plugin_utils.editor_options import EditorOptions
from klayout_plugin_utils.event_loop import EventLoop
from klayout_plugin_utils.str_enum_compat import StrEnum

from pin_pdk_info import *


CONFIG_KEY__PIN_TOOL_PLUGIN__PIN_LABEL = 'PinToolPlugin__pin_label'
CONFIG_KEY__PIN_TOOL_PLUGIN__PIN_WIDTH = 'PinToolPlugin__pin_width'
CONFIG_KEY__PIN_TOOL_PLUGIN__PIN_HEIGHT = 'PinToolPlugin__pin_height'


@dataclass
class PinToolConfig:
    short_layer_name: Optional[str] = None
    pin_label: str = 'pin_name'
    width: float = 0.13   # µm
    height: float = 0.13  # µm
    
    @classmethod
    def load(cls) -> PinToolConfig:
        if Debugging.DEBUG:
            debug("PinToolConfig.load")
            
        config = PinToolConfig()
        
        mw = pya.MainWindow.instance()
        pin_label = mw.get_config(CONFIG_KEY__PIN_TOOL_PLUGIN__PIN_LABEL)
        width_str = mw.get_config(CONFIG_KEY__PIN_TOOL_PLUGIN__PIN_WIDTH)
        height_str = mw.get_config(CONFIG_KEY__PIN_TOOL_PLUGIN__PIN_HEIGHT)

        if pin_label is not None:
            config.pin_label = pin_label
            
        if width_str is not None:
            config.width = float(width_str)
            
        if height_str is not None:
            config.height = float(height_str)
            
        return config
    
    def save(self):
        if Debugging.DEBUG:
            debug("PinToolConfig.save")
            
        mw = pya.MainWindow.instance()
        
        mw.set_config(CONFIG_KEY__PIN_TOOL_PLUGIN__PIN_LABEL, self.pin_label)
        mw.set_config(CONFIG_KEY__PIN_TOOL_PLUGIN__PIN_WIDTH, str(self.width))
        mw.set_config(CONFIG_KEY__PIN_TOOL_PLUGIN__PIN_HEIGHT, str(self.height))


class PinToolSetupDock(pya.QDockWidget):
    def __init__(self):
        super().__init__()
        self.setupWidget = PinToolSetupWidget()
        self.setWidget(self.setupWidget)
        self.setWindowTitle("Pin Tool")

    def navigateToNextTextField(self):
        self.setupWidget.navigateToNextTextField()
        
    def set_pdk_info(self, pdk_info: Optional[PinPDKInfo]):
        self.setupWidget.set_pdk_info(pdk_info)
        
    def set_config(self, config: PinToolConfig):
        self.setupWidget.set_config(config)

    def config_from_ui(self) -> PinToolConfig:
        return self.setupWidget.config_from_ui()
        
        
class PinToolSetupWidget(pya.QWidget):

    def __init__(self):
        super().__init__()
        self.layer_label = pya.QLabel('<span style="text-decoration: underline;">Layer:</span>')
        self.layer_value = pya.QComboBox()
        self.layer_value.addItems(['None selected'])
        self.layer_status = pya.QLabel('')

        mw = pya.MainWindow.instance()

        self.pin_label = pya.QLabel('<span style="text-decoration: underline;">Pin:</span>')
        self.pin_value = pya.QLineEdit('pin_name')

        self.w_label = pya.QLabel('<span style="text-decoration: underline;">Width:</span>')
        self.w_value = pya.QDoubleSpinBox()
        self.w_unit = pya.QLabel('µm')
        self.w_value.setValue(0.13)
        
        self.h_label = pya.QLabel('<span style="text-decoration: underline;">Height:</span>')
        self.h_value = pya.QDoubleSpinBox()
        self.h_unit = pya.QLabel('µm')
        self.h_value.setValue(0.13)

        self.spacer_item = pya.QSpacerItem(0, 20, pya.QSizePolicy.Minimum, pya.QSizePolicy.Fixed)
        self.cancel_info = pya.QLabel('<span style="color: grey;"><span style="text-decoration: underline;">Hint:</span> Esc to cancel</span>')
        
        self.layout = pya.QGridLayout()
        self.layout.setSpacing(10)
        self.layout.setVerticalSpacing(5)
        self.layout.addWidget(self.layer_label,   0, 0)
        self.layout.addWidget(self.layer_value,   0, 1)
        self.layout.addWidget(self.layer_status,  0, 2)
        self.layout.addWidget(self.pin_label,     1, 0)
        self.layout.addWidget(self.pin_value,     1, 1)
        self.layout.addWidget(self.w_label,       2, 0)
        self.layout.addWidget(self.w_value,       2, 1)
        self.layout.addWidget(self.w_unit,        2, 2)
        self.layout.addWidget(self.h_label,       3, 0)
        self.layout.addWidget(self.h_value,       3, 1)
        self.layout.addWidget(self.h_unit,        3, 2)
        self.layout.addItem(self.spacer_item)
        self.layout.addWidget(self.cancel_info,   4, 0)
        self.layout.setRowStretch(5, 3)
        self.setLayout(self.layout)

        self.layer_value.currentTextChanged.connect(self.on_pin_layer_changed)
         
    def hideEvent(self, event):
        event.accept()
        
    def navigateToNextTextField(self):
        self.focusNextPrevChild(next=True)

    def focusNextPrevChild(self, next: bool) -> bool:
        if next:
            if self.pin_value.hasFocus():
                self.w_value.setFocus()
                self.w_value.selectAll()
            elif self.w_value.hasFocus():
                self.h_value.setFocus()
                self.h_value.selectAll()
            else:
                self.pin_value.setFocus()
                self.pin_value.selectAll()
        else:
            if self.h_value.hasFocus():
                self.w_value.setFocus()
                self.w_value.selectAll()
            elif self.pin_value.hasFocus():
                self.h_value.setFocus()
                self.h_value.selectAll()
            else:
                self.pin_value.setFocus()        
                self.pin_value.selectAll()
        return True
        
    def on_pin_layer_changed(self):
        config = self.config_from_ui()
        self.set_config(config)
        
    def set_pdk_info(self, pdk_info: Optional[PinPDKInfo]):
        self.layer_value.clear()
        new_items = ['None selected']
        if pdk_info is not None:
            for pli in pdk_info.pin_layer_infos:
                new_items.append(pli.short_layer_name)
        self.layer_value.addItems(new_items)
        
    def set_config(self, config: PinToolConfig):
        if config.short_layer_name is None:
            self.layer_value.setCurrentText('None selected')
            self.layer_status.setText(
                '<span style="color:blue; font-weight:bold;">⬅</span> '
                '<span style="font-weight:bold; color:blue;">Next</span>'
            )
        else:
            self.layer_value.setCurrentText(config.short_layer_name)
            self.layer_status.setText('✅')
        
        self.pin_value.setText(config.pin_label)
        self.w_value.setValue(config.width)
        self.h_value.setValue(config.height)

    def config_from_ui(self) -> PinToolConfig:
        lv = self.layer_value.currentText
        short_layer_name = None if lv == 'None selected' else lv
        return PinToolConfig(short_layer_name, self.pin_value.text, self.w_value.value, self.h_value.value)


class PinToolPlugin(pya.Plugin):
    def __init__(self, view: pya.LayoutView):
        super().__init__()

        script_dir = Path(__file__).resolve().parent
        self.pdk_info_factory = PinPDKInfoFactory(search_path=[script_dir / '..' / 'pdks'])
        self.pdk_info = None
        self.pin_layer_info = None
        
        self.editor_options = None
        
        self.setupDock      = None
        
        self.view            = view
        self.view.on_layer_list_changed += self.on_layer_list_changed
        self.view.on_selection_changed += self.on_selection_changed
        self.view.on_apply_technology += self.on_apply_technology

        self.markers = []

    def on_layer_list_changed(self, idx: int):
        if Debugging.DEBUG:
            debug(f"PinToolPlugin.on_layer_list_changed, "
                  f"for cell view {self.cell_view.cell_name}")

    def on_current_layer_changed(self, idx: int):
        if Debugging.DEBUG:
            debug(f"PinToolPlugin.on_current_layer_changed, "
                  f"for cell view {self.cell_view.cell_name}")
    
    def on_selection_changed(self):
        if Debugging.DEBUG:
            debug(f"PinToolPlugin.on_selection_changed, "
                  f"for cell view {self.cell_view.cell_name}")
    
    def on_apply_technology(self):
        if Debugging.DEBUG:
            debug(f"PinToolPlugin.on_apply_technology, "
                  f"for cell view {self.cell_view.cell_name}")
    
    @property
    def cell_view(self) -> pya.CellView:
        return self.view.active_cellview()

    @property
    def layout(self) -> pya.Layout:
        return self.cell_view.layout()
        
    @property
    def tech(self) -> pya.Technology:
        return self.layout.technology()
    
    @property
    def dbu(self) -> float:
        return self.layout.dbu
    
    def show_editor_options(self):
        mw = pya.Application.instance().main_window()
    
        # NOTE: if we directly call the Editor Options menu action
        #       the GUI immediately will switch back to the Librariew view
        #       so we enqueue it into the event loop
        EventLoop.defer(lambda w=mw: w.call_menu('cm_edit_options'))
    
    def get_current_layer_name(self) -> Optional[str]:
        iter = self.view.current_layer
        if iter is None:
            return None
        current_layer = iter.current()
        if current_layer is None:
            return None
        name = current_layer.name or current_layer.source
        if name == '*/*@*':
            return None
        return name
    
    def update_tech(self):
        tech = self.tech
        self.pdk_info = None
        if tech is None:
            if Debugging.DEBUG:
                debug(f"PinToolPlugin.activate, can't find technology")
        else:
            self.pdk_info = self.pdk_info_factory.pdk_info(tech.name)
        
        if self.setupDock is not None:
            self.setupDock.set_pdk_info(self.pdk_info)                
    
    def activated(self):
        view_is_visible = self.view.widget().isVisible()
        if Debugging.DEBUG:
            debug(f"PinToolPlugin.activated, "
                  f"for cell view {self.cell_view.cell_name}, "
                  f"is visible: {view_is_visible}")
            debug(f"viewport trans: {self.view.viewport_trans()}")
        if not view_is_visible:
            return

        script_dir = Path(__file__).resolve().parent
        self.pdk_info_factory = PinPDKInfoFactory(search_path=[script_dir / '..' / 'pdks'])
    
        if not(self.setupDock):
            mw   = pya.Application.instance().main_window()
            self.setupDock = PinToolSetupDock()
            mw.addDockWidget(pya.Qt_DockWidgetArea.RightDockWidgetArea, self.setupDock)
        self.setupDock.show()
        
        self.editor_options = EditorOptions(view=self.view)

        # NOTE: defer twice, strange but necessary
        EventLoop.defer(self.navigateToNextTextField)        

        short_layer_name: Optional[str] = None

        config = PinToolConfig.load()
        
        self.pin_layer_info = None
        
        self.update_tech()

        if self.pdk_info is not None:            
            current_layer_name = self.get_current_layer_name()
            if current_layer_name is None:
                if Debugging.DEBUG:
                    debug(f"PinToolPlugin.activate, no layer is selected")
            else:
                self.pin_layer_info = self.pdk_info.pin_layer_info(current_layer_name)
                if self.pin_layer_info is not None:
                    config.short_layer_name = self.pin_layer_info.short_layer_name

        self.setupDock.set_config(config)
    
    def navigateToNextTextField(self):
        EventLoop.defer(self.setupDock.navigateToNextTextField)
    
    def deactivated(self):
        if Debugging.DEBUG:
            debug("PinToolPlugin.deactivated")
        
        self.clear_markers()
        self.pdk_info = None
        self.pin_layer_info = None
        
        self.ungrab_mouse()
        if self.setupDock:
            self.setupDock.hide()
    
    def deactivate(self):
        if Debugging.DEBUG:
            debug("PinToolPlugin.deactive")
        esc_key  = 16777216 
        keyPress = pya.QKeyEvent(pya.QKeyEvent.KeyPress, esc_key, pya.Qt.NoModifier)
        pya.QApplication.sendEvent(self.view.widget(), keyPress)        
    
    def menu_activated(self, symbol: str) -> bool:
        if Debugging.DEBUG:
            debug(f"PinToolPlugin.menu_activated: symbol={symbol}")
            
        if symbol == 'technology_selector:apply_technology':
            if Debugging.DEBUG:
                debug(f"PinToolPlugin.menu_activated: "
                      f"pya.CellView.active().technology().name={pya.CellView.active().technology} (NOTE: old, that's why we need defer)")
            # NOTE: we have to defer, otherwise the CellView won't have the new tech yet
            EventLoop.defer(self.technology_applied)
    
        return False
    
    def technology_applied(self):
        new_tech_name = pya.CellView.active().technology
        if Debugging.DEBUG:
            debug(f"PinToolPlugin.technology_applied, "
                  f"for cell view {self.cell_view.cell_name}, "
                  f"tech: {new_tech_name}")
            
        try:
            self.update_tech()
        except Exception as e:
            print("PinToolPlugin.technology_applied caught an exception", e)
            traceback.print_exc()        
    
    def visible_layer_indexes(self) -> List[int]:
        idxs = []
        for lref in self.view.each_layer():
            if lref.visible and lref.valid:
                if lref.layer_index() == -1:  # hidden by the user
                    continue
                # print(f"layer is visible, name={lref.name}, idx={lref.layer_index()}, "
                #       f"marked={lref.marked} cellview={lref.cellview()}, "
                #      f"source={lref.source}")
                idxs.append(lref.layer_index())
        return idxs
    
    def viewport_adjust(self, v: int) -> int:
        trans = pya.CplxTrans(self.view.viewport_trans(), self.dbu)
        return v / trans.mag
    
    @property
    def max_distance(self) -> int:
        return self.viewport_adjust(20)
    
    def clear_markers(self):
        for marker in self.markers:
            marker._destroy()
        self.markers = []

    def preview_markers_for_cursor(self, dpoint: pya.DPoint) -> List[pya.Marker]:
        pt = dpoint.to_itype(self.dbu)
        markers = []
    
        point_marker = pya.Marker(self.view)
        point_marker.line_style     = 1
        point_marker.line_width     = 2
        point_marker.vertex_size    = 0
        point_marker.dither_pattern = 0
        d = self.viewport_adjust(5)
        marker_box = pya.Box(pya.Point(pt.x - d, pt.y - d), 
                             pya.Point(pt.x + d, pt.y + d))
        point_marker.set(marker_box.to_dtype(self.dbu))
        markers += [point_marker]
        
        return markers
    
    def mouse_moved_event(self, dpoint: pya.DPoint, buttons: int, prio: bool):
        if prio:
            if self.editor_options is None:
                return False  # not fully activated yet
                
            # # Hotspot, don't log this       
            # if Debugging.DEBUG:
            #   debug(f"PinToolPlugin.mouse_moved_event: mouse moved event, p={dpoint}, prio={prio}")
            snapped_to_cursor = self.editor_options.snap_to_grid_if_necessary(dpoint)
            self.markers = self.preview_markers_for_cursor(snapped_to_cursor)
            return True
        return False
        
    def mouse_click_event(self, dpoint: pya.DPoint, buttons: int, prio: bool):
        if prio:
            if buttons in [8]:  # Left click
                snapped_to_cursor = self.editor_options.snap_to_grid_if_necessary(dpoint)
                self.commit_place_pin(snapped_to_cursor)
                
            if buttons in [16, 32]:
                self.clear_markers()

            return True
        return False
        
    def key_event(self, key: int, buttons: int):
        if Debugging.DEBUG:
            debug(f"PinToolPlugin.key_event: key={key}, buttons={buttons}")

        match key:
            case pya.KeyCode.Tab:
                if Debugging.DEBUG:
                    debug("PinToolPlugin.key_event: tab!")
                if self.setupDock is not None:
                    self.clear_markers()
                    self.setupDock.navigateToNextTextField()
                    return True
        return False                
        
    def layer_properties_for_layer_name(self, name: str) -> Optional[pya.LayerPropertiesNodeRef]:
        iter = self.view.begin_layers()
        while not iter.at_end():
            lp = iter.current()
            if lp.name == name:
                return lp
            if lp.source == name:
                return lp
            iter.next()
        return None
        
    def layer_number_for_layer_name(self, name: str) -> int:
        lp = self.layer_properties_for_layer_name(name)
        if lp is None:
            return -1
        li = lp.layer_index()
        if li != -1:
            return li
        # e.g. for IHP Metal3.pin, this did return -1
        li = self.layout.layer(lp.source_layer, lp.source_datatype)
        return li
        
    def commit_place_pin(self, dpoint: pya.DPoint):
        self.clear_markers()

        config = self.setupDock.config_from_ui()

        if config.short_layer_name is None:
            mb = pya.QMessageBox()
            mb.setIcon(pya.QMessageBox.Critical)
            mb.setWindowTitle('Error')
            mb.setText('Please select a layer first')
            mb.setStandardButtons(pya.QMessageBox.Ok)
            mb.exec_()
            
            if Debugging.DEBUG:
                debug(f"PinToolPlugin.commit_place_pin, can't find PinLayerInfo, ignoring this request")
            return
        else:
            self.pin_layer_info = self.pdk_info.pin_layer_info(config.short_layer_name)
            if self.pin_layer_info is not None:
                config.short_layer_name = self.pin_layer_info.short_layer_name
        
        cell_index = self.cell_view.cell_index
        dbox = pya.DBox(dpoint.x - config.width/2.0, dpoint.y - config.height/2.0,
                        dpoint.x + config.width/2.0, dpoint.y + config.height/2.0)
        box = dbox.to_itype(self.dbu)
            
        self.view.transaction("place pin")
        try:
            for ln in self.pdk_info.layers_of_groups(self.pin_layer_info.pin_layers):
                r = pya.Region()
                r.insert(box)
                lyr = self.layer_number_for_layer_name(ln)
                if lyr == -1:
                    raise Exception(f"PinToolPlugin.commit_place_pin, can't find layer index for layer {ln})")
                self.layout.insert(cell_index, lyr, r)
                
            for ln in self.pdk_info.layers_of_groups(self.pin_layer_info.label_layers):
                dt = pya.DText(config.pin_label, dpoint.x, dpoint.y)
                t = pya.Texts(dt.to_itype(self.dbu))
                lyr = self.layer_number_for_layer_name(ln)
                if lyr == -1:
                    raise Exception(f"PinToolPlugin.commit_place_pin, can't find layer index for layer {ln})")
                self.layout.insert(cell_index, lyr, t)
                
                config.save()
        except Exception as e:
            print("PinToolPlugin.commit_place_pin caught an exception", e)
            traceback.print_exc()
        finally:
            self.view.commit()
            # NOTE: stay active until user types ESC
            # self.deactivate()


class PinToolPluginFactory(pya.PluginFactory):
    def __init__(self):
        super().__init__()
        
        directory_containing_this_script = os.path.realpath(os.path.dirname(__file__))
        icon_path = os.path.join(directory_containing_this_script, 'icons', 'pin_32px.png')
        
        self.register(-1000, "Pin Tool", "Pin (Shift+P)", icon_path)
  
    def create_plugin(self, manager, root, view):
        return PinToolPlugin(view)


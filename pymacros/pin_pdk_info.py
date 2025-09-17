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
from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
import sys
from typing import *

from klayout_plugin_utils.debugging import debug, Debugging
from klayout_plugin_utils.str_enum_compat import StrEnum
from klayout_plugin_utils.dataclass_dict_helpers import dataclass_from_dict


LayerUniqueName = str
LayerGroupUniqueName = str


@dataclass
class NamedLayerGroup:
    name: LayerGroupUniqueName
    layers: List[LayerUniqueName]


@dataclass
class PinLayerInfo:
    short_layer_name: str                   # e.g. Metal1, GatPoly, ...
    related_layers: LayerGroupUniqueName    # e.g. Metal1.drawing, Metal1.pin, Metal1.text, Metal1.dumm, Metal1.label, ...
                                            # helps us to find the appropriate layers,
                                            # if any of those related layer is selected
    pin_layers: LayerGroupUniqueName        # Metal1.pin  (if multiple, the pin will be created on all of those)
    label_layers: LayerGroupUniqueName       # Metal1.text   (if multiple, the label will be created on all of those)


#--------------------------------------------------------------------------------

@dataclass
class PinPDKInfo:
    tech_name: str
    layer_group_definitions: List[NamedLayerGroup]
    pin_layer_infos: List[PinLayerInfo]
    
    @classmethod
    def read_json(cls, path: Path) -> PinPDKInfo:
        with open(path) as f:
            data = json.load(f)
            return dataclass_from_dict(cls, data)
        
    def write_json(self, path: Path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=4)
            
    def layer_groups(self, names: List[LayerGroupUniqueName]) -> List[NamedLayerGroup]:
        return [g for g in self.layer_group_definitions if g.name in names]
        
    def layers_of_groups(self, names: List[LayerGroupUniqueName]) -> List[LayerUniqueName]:
        layer_groups = self.layer_groups(names)
        return list(set([l for g in layer_groups for l in g.layers]))
        
    def pin_layer_info(self, related_layer: LayerUniqueName) -> PinLayerInfo:
        for pli in self.pin_layer_infos:
            if related_layer == pli.short_layer_name:
                return pli
            related_layers = self.layers_of_groups(pli.related_layers + pli.pin_layers + pli.label_layers)
            if related_layer in related_layers:
                return pli


class PinPDKInfoFactory:
    def __init__(self, search_path: List[Path]):
        self._pdk_infos_by_tech_name: Dict[str, PinPDKInfo] = {}
        
        json_files = sorted({f for p in search_path for f in p.glob('*.json')})
        for f in json_files:
            try:
                pdk_info = PinPDKInfo.read_json(f)
                self._pdk_infos_by_tech_name[pdk_info.tech_name] = pdk_info
            except Exception as e:
                print(f"Failed to parse PDK info file {f}, skipping this file…", e)
                
    def pdk_info(self, tech_name: str) -> Optional[PinPDKInfo]:
        return self._pdk_infos_by_tech_name.get(tech_name, None)
            
    @property
    def pdk_infos_by_tech_name(self) -> Dict[str, PinPDKInfo]:
        return self._pdk_infos_by_tech_name
            
#--------------------------------------------------------------------------------

def dump_example_pdk_info():
    def met_layers(name: str) -> List[str]:
        return [f"{name}.drawing", f"{name}.pin", f"{name}.text", f"{name}.label"]

    def pin_layer_info(prefix: str, key: str, i: int) -> List[PinLayerInfo]:
        return [
            PinLayerInfo(short_layer_name=f"{prefix}{i}", 
                         related_layers=[f"{prefix}{i}.RelatedLayers"],
                         pin_layers=[f"{prefix}{i}.PinLayers"],
                         label_layers=[f"{prefix}{i}.LabelLayers"])
        ]

    pin_layer_infos: List[PinLayerInfo] = [
        PinLayerInfo(short_layer_name="nBuLay", 
                     related_layers=["nBuLay.RelatedLayers"],
                     pin_layers=["nBuLay.PinLayers"],
                     label_layers=["nBuLay.LabelLayers"]),
        PinLayerInfo(short_layer_name="NWell", 
                     related_layers=["NWell.RelatedLayers"],
                     pin_layers=["NWell.PinLayers"],
                     label_layers=["NWell.LabelLayers"]),
        PinLayerInfo(short_layer_name="GatPoly", 
                     related_layers=["GatPoly.RelatedLayers"],
                     pin_layers=["GatPoly.PinLayers"],
                     label_layers=["GatPoly.LabelLayers"])
    ]
    for i in range(1, 6):
        pin_layer_infos += pin_layer_info(prefix='Metal', key=str(i), i=i)
    for i in range(1, 3):
        pin_layer_infos += pin_layer_info(prefix='TopMetal', key=str(5+i), i=i)
    pin_layer_infos += [
        PinLayerInfo(short_layer_name="IND", 
                     related_layers=["IND.RelatedLayers"],
                     pin_layers=["IND.PinLayers"],
                     label_layers=["IND.LabelLayers"])
    ]

    pi = PinPDKInfo(
        tech_name='sg13g2',
        layer_group_definitions = [
            NamedLayerGroup(name='nBuLay.PinLayers', layers=['nBuLay.pin']),
            NamedLayerGroup(name='nBuLay.LabelLayers', layers=['nBuLay.label']),
            NamedLayerGroup(name='nBuLay.RelatedLayers',  layers=['nBuLay.pin', 'nBuLay.drawing', 'nBuLay.label', 
                                                                  'nBuLay.net', 'nBuLay.boundary', 'nBuLay.block']),

            NamedLayerGroup(name='NWell.PinLayers', layers=['NWell.pin']),
            NamedLayerGroup(name='NWell.LabelLayers', layers=['NWell.label']),
            NamedLayerGroup(name='NWell.RelatedLayers',  layers=['NWell.pin', 'NWell.drawing', 'NWell.label', 
                                                                 'NWell.net', 'NWell.boundary']),

            NamedLayerGroup(name='GatPoly.PinLayers', layers=['GatPoly.pin']),
            NamedLayerGroup(name='GatPoly.LabelLayers', layers=['GatPoly.label']),
            NamedLayerGroup(name='GatPoly.RelatedLayers',  layers=['GatPoly.pin', 'GatPoly.drawing', 'GatPoly.label', 
                                                                   'GatPoly.net', 'GatPoly.boundary', 'GatPoly.nofill']),
            
            NamedLayerGroup(name='Metal1.PinLayers', layers=['Metal1.pin']),
            NamedLayerGroup(name='Metal1.LabelLayers', layers=['Metal1.text']),
            NamedLayerGroup(name='Metal1.RelatedLayers',  layers=met_layers('Metal1') + ['Metal1.diffprb']),

            NamedLayerGroup(name='Metal2.PinLayers', layers=['Metal2.pin']),
            NamedLayerGroup(name='Metal2.LabelLayers', layers=['Metal2.text']),
            NamedLayerGroup(name='Metal2.RelatedLayers',  layers=met_layers('Metal2')),

            NamedLayerGroup(name='Metal3.PinLayers', layers=['Metal3.pin']),
            NamedLayerGroup(name='Metal3.LabelLayers', layers=['Metal3.text']),
            NamedLayerGroup(name='Metal3.RelatedLayers',  layers=met_layers('Metal3')),

            NamedLayerGroup(name='Metal4.PinLayers', layers=['Metal4.pin']),
            NamedLayerGroup(name='Metal4.LabelLayers', layers=['Metal4.text']),
            NamedLayerGroup(name='Metal4.RelatedLayers',  layers=met_layers('Metal4')),

            NamedLayerGroup(name='Metal5.PinLayers', layers=['Metal5.pin']),
            NamedLayerGroup(name='Metal5.LabelLayers', layers=['Metal5.text']),
            NamedLayerGroup(name='Metal5.RelatedLayers',  layers=met_layers('Metal5')),

            NamedLayerGroup(name='TopMetal1.PinLayers', layers=['TopMetal1.pin']),
            NamedLayerGroup(name='TopMetal1.LabelLayers', layers=['TopMetal1.text']),
            NamedLayerGroup(name='TopMetal1.RelatedLayers',  layers=met_layers('TopMetal1')),

            NamedLayerGroup(name='TopMetal2.PinLayers', layers=['TopMetal2.pin']),
            NamedLayerGroup(name='TopMetal2.LabelLayers', layers=['TopMetal2.text']),
            NamedLayerGroup(name='TopMetal2.RelatedLayers',  layers=met_layers('TopMetal2')),
            
            NamedLayerGroup(name='IND.PinLayers', layers=['IND.pin']),
            NamedLayerGroup(name='IND.LabelLayers', layers=['IND.text']),
            NamedLayerGroup(name='IND.RelatedLayers',  layers=['IND.pin', 'IND.drawing', 'IND.text']),            
        ],
        pin_layer_infos=pin_layer_infos
    )
     
    path = os.path.abspath('ihp-sg13g2.json')
    pi.write_json(path)
    print(f"Dumped example PDK Info file to {path}")


def test_parse():
    script_dir = Path(__file__).resolve().parent
    f = PinPDKInfoFactory(search_path=[script_dir / '..' / 'pdks'])
    for pi in f.pdk_infos_by_tech_name.values():
        json.dump(asdict(pi), sys.stdout, indent=4)

#--------------------------------------------------------------------------------

if __name__ == "__main__":
    dump_example_pdk_info()
    test_parse()


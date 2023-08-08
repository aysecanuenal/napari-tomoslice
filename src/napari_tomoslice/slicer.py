from enum import Enum, auto
from os import PathLike
from pathlib import Path
from typing import TypeVar

import napari
import napari_threedee as n3d
import numpy as np

from napari_tomoslice._constants import TOMOGRAM_LAYER_NAME, PLANE_NORMAL_VECTOR, \
    PLANE_THICKNESS
from napari_tomoslice.io import read_volume
from napari_tomoslice.utils import add_tomogram_to_viewer
from napari_tomoslice.widgets import SlicerControlsWidget
from napari_tomoslice.console import console

Annotator = TypeVar('Annotator')


class AnnotationMode(Enum):
    DISABLED = auto()
    POINT = auto()
    PATH = auto()
    SPHERE = auto()


class Slicer:
    viewer: napari.viewer.Viewer
    widget: SlicerControlsWidget
    annotator: Annotator | None

    tomogram_path: Path | None
    annotation_mode: AnnotationMode

    def __init__(self, viewer: napari.viewer.Viewer):
        self.viewer = viewer
        self.widget = SlicerControlsWidget(self)
        self.viewer.window.add_dock_widget(
            self.widget,
            name='tomoslice controls',
            area='left',
            allowed_areas=['left'],
        )

        self._tomogram_path = None
        self._annotation_mode = AnnotationMode.DISABLED

    @property
    def tomogram_path(self) -> Path | None:
        return self._tomogram_path

    @tomogram_path.setter
    def tomogram_path(self, value: PathLike):
        self._tomogram_path = Path(value) if value is not None else None

        # update gui
        self.widget.tomogram_selector.line_edit.setText(str(self._tomogram_path))
        self.load_tomogram(self._tomogram_path)

    @property
    def annotation_mode(self) -> AnnotationMode:
        return self._annotation_mode

    @annotation_mode.setter
    def annotation_mode(self, value: AnnotationMode):
        self._annotation_mode = value

        # ensure correct annotator is loaded
        if TOMOGRAM_LAYER_NAME not in self.viewer.layers:
            console.log('no tomogram in viewer - not starting annotator')
        else:
            console.log('starting annotator')
            self.start_annotator()

        # update gui
        buttons = self.widget.annotator_button_group
        mode_to_button = {
            AnnotationMode.DISABLED: 999,
            AnnotationMode.POINT: buttons.point_button,
            AnnotationMode.PATH: buttons.path_button,
            AnnotationMode.SPHERE: buttons.sphere_button,
        }
        for button in buttons:
            if button is not mode_to_button[value]:
                button.setChecked(False)

    def load_tomogram(self, path: Path):
        console.log(f'loading tomogram from {path}')
        volume = read_volume(path)
        console.log(f'array of shape {volume.shape} loaded')
        add_tomogram_to_viewer(tomogram=volume, viewer=self.viewer)
        console.log('tomogram added to viewer')

    def start_annotator(self):
        if self.annotation_mode is AnnotationMode.POINT:
            self.start_point_annotator()
        elif self.annotation_mode is AnnotationMode.PATH:
            self.start_path_annotator()
        elif self.annotation_mode is AnnotationMode.SPHERE:
            self.start_sphere_annotator()

    def start_point_annotator(self):
        points_layer = n3d.data_models.N3dPoints(data=[]).as_layer()
        self.viewer.add_layer(points_layer)
        self.annotator = n3d.annotators.PointAnnotator(
            viewer=self.viewer,
            image_layer=self.viewer.layers[TOMOGRAM_LAYER_NAME],
            points_layer=points_layer,
            enabled=True
        )
        console.log('point annotator started')
        self.viewer.layers.selection.active = self.viewer.layers[TOMOGRAM_LAYER_NAME]

    def start_path_annotator(self):
        points_layer = n3d.data_models.N3dPaths(data=[]).as_layer()
        self.viewer.add_layer(points_layer)
        self.annotator = n3d.annotators.PathAnnotator(
            viewer=self.viewer,
            image_layer=self.viewer.layers[TOMOGRAM_LAYER_NAME],
            points_layer=points_layer,
            enabled=True,
        )
        console.log('path annotator started')

    def start_sphere_annotator(self):
        points_layer = n3d.data_models.N3dSpheres(centers=[], radii=[]).as_layer()
        self.viewer.add_layer(points_layer)
        self.annotator = n3d.annotators.SphereAnnotator(
            viewer=self.viewer,
            image_layer=self.viewer.layers[TOMOGRAM_LAYER_NAME],
            points_layer=points_layer,
            enabled=True,
        )
        console.log('sphere annotator started')

from neuroglancer_annotation_ui import EasyViewer, annotation, set_static_content_source
from neuroglancer_annotation_ui.utils import default_static_content_source
from annotationframeworkclient import FrameworkClient
import pandas as pd
import numpy as np
from IPython.display import HTML
from .utils import bucket_of_values

DEFAULT_IMAGE_LAYER = 'img'
DEFAULT_SEG_LAYER = 'seg'
DEFAULT_ANNO_LAYER = 'anno'


class LayerConfigBase(object):
    """Base class for configuring layers

    Parameters
    ----------
    name : str
        Layer name for reference and display
    type : str
        Layer type. Usually handled by the subclass
    source : str
        Datasource for the layer
    color : str
        Hex string (with starting hash).

    """

    def __init__(self,
                 name,
                 type,
                 source,
                 color,
                 ):
        self._config = dict(type=type,
                            name=name,
                            source=source,
                            color=color,
                            )

    @property
    def type(self):
        return self._config.get('type', None)

    @property
    def name(self):
        return self._config.get('name', None)

    @name.setter
    def name(self, n):
        self._config['name'] = n

    @property
    def source(self):
        return self._config.get('source', None)

    @source.setter
    def source(self, s):
        self._config['source'] = s

    @property
    def color(self):
        return self._config.get('color', None)

    @color.setter
    def color(self, c):
        self._config.set['color'] = c

    def _render_layer(self, viewer, data):
        """ Subclasses implement specific rendering rules
        """
        return viewer


class ImageLayerConfig(LayerConfigBase):
    """Image layer configuration class.

    This provides the rules for setting up an image layer in neuroglancer.

    Parameters
    ----------
    source : str
        Cloudpath to an image source
    name : str, optional
        Name of the image layer. By default, 'img'.
    """

    def __init__(self,
                 source,
                 name=DEFAULT_IMAGE_LAYER,
                 ):
        super(ImageLayerConfig, self).__init__(
            name=name, type='image', source=source, color=None)

    def _render_layer(self, viewer, data):
        viewer.add_image_layer(self.name, self.source)
        return viewer


class SelectionMapper(object):
    """Class for configuring object selections based on root id

    Parameters
    ----------
    data_columns : str or list, optional
        Name (or list of names) of the data columns to get ids from. Default is None.
    fixed_ids : list, optional
        List of ids to select irrespective of data.
    """

    def __init__(self, data_columns=None, fixed_ids=None):
        if isinstance(data_columns, str):
            data_columns = [data_columns]
        self._config = dict(data_columns=data_columns,
                            fixed_ids=fixed_ids)

    @property
    def data_columns(self):
        if self._config.get('data_columns', None) is None:
            return []
        else:
            return self._config.get('data_columns')

    @property
    def fixed_ids(self):
        if self._config.get('fixed_ids', None) is None:
            return []
        else:
            return self._config.get('fixed_ids', None)

    def selected_ids(self, data):
        """ Uses the rules to generate a list of ids from a dataframe.
        """
        selected_ids = [np.array(self.fixed_ids, dtype=np.int64)]
        if data is not None:
            for col in self.data_columns:
                selected_ids.append(data[col])
        return np.concatenate(selected_ids)


class SegmentationLayerConfig(LayerConfigBase):
    """Configuration class for segmentatoin layers

    Parameters
    ----------
    source : str
        Segmentation source

    Returns
    -------
    [type]
        [description]
    """

    def __init__(self,
                 source,
                 name=DEFAULT_SEG_LAYER,
                 selected_ids_column=None,
                 fixed_ids=None,
                 ):
        super(SegmentationLayerConfig, self).__init__(
            name=name, type='segmentation', source=source, color=None)
        if selected_ids_column is not None or fixed_ids is not None:
            self._selection_map = SelectionMapper(
                data_columns=selected_ids_column,
                fixed_ids=fixed_ids)
        else:
            self._selection_map = None

    def add_selection_map(self, selected_ids_column=None, fixed_ids=None):
        if self._selection_map is not None:
            if isinstance(selected_ids_column, str):
                selected_ids_column = [selected_ids_column]
            data_columns = self._selection_map.data_columns.extend(
                selected_ids_column)
            fixed_ids = self._selection_map.fixed_ids.extend(fixed_ids)

        self._selection_map = SelectionMapper(
            data_columns=data_columns,
            fixed_ids=fixed_ids)

    def _render_layer(self, viewer, data):
        viewer.add_segmentation_layer(self.name, self.source)
        if self._selection_map is not None:
            selected_ids = self._selection_map.selected_ids(data)
            viewer.add_selected_objects(self.name, selected_ids)
        return viewer


class AnnotationLayerConfig(LayerConfigBase):
    """Configuration class for annotation layers

    Parameters
    ----------
    name : str, optional
        Layer name. By default, 'annos'
    color : str, optional
        Hex color code with an initial #. By default, None
    linked_segmentation_layer : str, optional
        Name of a linked segmentation layer for selected ids. By default, None
    mapping_rules : PointMapper, LineMapper, SphereMapper or list, optional
        One rule or a list of rules mapping data to annotations. By default, []
    tags : list, optional
        List of tags for the layer.
    Returns
    -------
    [type]
        [description]
    """

    def __init__(self,
                 name=DEFAULT_ANNO_LAYER,
                 color=None,
                 linked_segmentation_layer=None,
                 mapping_rules=[],
                 tags=None):
        super(AnnotationLayerConfig, self).__init__(
            name=name, type='annotation', color=color, source=None)
        self._config['linked_segmentation_layer'] = linked_segmentation_layer
        if issubclass(type(mapping_rules), AnnotationMapperBase):
            mapping_rules = [mapping_rules]
        self._annotation_map_rules = mapping_rules
        self._tags = tags

    @property
    def linked_segmentation_layer(self):
        return self._config.get('linked_segmentation_layer', None)

    def _render_layer(self, viewer, data):
        viewer.add_annotation_layer(self.name,
                                    color=self.color,
                                    linked_segmentation_layer=self.linked_segmentation_layer,
                                    tags=self._tags)
        annos = []
        for rule in self._annotation_map_rules:
            annos.extend(rule._render_data(data))
        viewer.add_annotations(self.name, annos)


class AnnotationMapperBase(object):
    def __init__(self,
                 type,
                 data_columns,
                 description_column,
                 linked_segmentation_column,
                 ):

        self._config = dict(type=type,
                            data_columns=data_columns,
                            description_column=description_column,
                            linked_segmentation_column=linked_segmentation_column,
                            )

    @property
    def type(self):
        return self._config.get('type', None)

    @property
    def data_columns(self):
        return self._config.get('data_columns', None)

    @property
    def description_column(self):
        return self._config.get('description_columns', None)

    @property
    def linked_segmentation_column(self):
        return self._config.get('linked_segmentation_column', None)

    def _render_data(self, data):
        # Set per subclass
        return None

    def _linked_segmentations(self, data):
        if self.linked_segmentation_column is not None:
            seg_array = np.vstack(
                data[self.linked_segmentation_column].values)
            linked_segs = [row[~np.isnan(row)].astype(int)
                           for row in seg_array]
        else:
            linked_segs = [None for x in range(len(data))]
        return linked_segs

    def _descriptions(self, data):
        if self.description_column is not None:
            descriptions = data[self.description_column].values
        else:
            descriptions = [None for x in range(len(data))]
        return descriptions


class PointMapper(AnnotationMapperBase):
    def __init__(self,
                 point_column,
                 description_column=None,
                 linked_segmentation_column=None):

        super(PointMapper, self).__init__(type='point',
                                          data_columns=[point_column],
                                          description_column=None,
                                          linked_segmentation_column=linked_segmentation_column,
                                          )

    def _render_data(self, data):
        col = self.data_columns[0]
        relinds = ~pd.isnull(data[col])

        pts = np.vstack(data[col][relinds])
        descriptions = self._descriptions(data[relinds])
        linked_segs = self._linked_segmentations(data[relinds])

        annos = [annotation.point_annotation(pt,
                                             description=d,
                                             linked_segmentation=ls) for
                 pt, d, ls in zip(pts, descriptions, linked_segs)]
        return annos


class LineMapper(AnnotationMapperBase):
    def __init__(self,
                 point_column_a,
                 point_column_b,
                 description_column=None,
                 linked_segmentation_layer=None,
                 linked_segmentation_column=None):

        super(LineMapper, self).__init__(type='line',
                                         data_columns=[
                                              point_column_a, point_column_b],
                                         description_column=None,
                                         linked_segmentation_column=linked_segmentation_column,
                                         )

    def _render_data(self, data):
        colA, colB = self.data_columns

        relinds = np.logical_and(~pd.isnull(
            data[colA]), ~pd.isnull(data[colB]))

        ptAs = np.vstack(data[colA][relinds])
        ptBs = np.vstack(data[colB][relinds])
        descriptions = self._descriptions(data[relinds])
        linked_segs = self._linked_segmentations(data[relinds])

        annos = [annotation.line_annotation(ptA, ptB,
                                            description=d,
                                            linked_segmentation=ls) for
                 ptA, ptB, d, ls in zip(ptAs, ptBs, descriptions, linked_segs)]
        return annos


class SphereMapper(AnnotationMapperBase):
    def __init__(self,
                 center_column,
                 radius_column,
                 description_column=None,
                 linked_segmentation_layer=None,
                 linked_segmentation_column=None,
                 z_multiplier=0.1):

        super(SphereMapper, self).__init__(type='sphere',
                                           data_columns=[
                                               center_column, radius_column],
                                           description_column=None,
                                           linked_segmentation_column=linked_segmentation_column,
                                           )
        self._z_multiplier = z_multiplier

    def _render_data(self, data):
        col_ctr, col_rad = self.data_columns
        relinds = np.logical_and(~pd.isnull(
            data[col_ctr]), ~pd.isnull(data[col_rad]))

        pts = np.vstack(data[col_ctr][relinds])
        rs = data[col_rad][relinds].values
        descriptions = self._descriptions(data[relinds])
        linked_segs = self._linked_segmentations(data[relinds])
        annos = [annotation.sphere_annotation(pt, r,
                                              description=d,
                                              linked_segmentation=ls,
                                              z_multiplier=self._z_multiplier) for
                 pt, r, d, ls in zip(pts, rs, descriptions, linked_segs)]
        return annos


class StateBuilder():
    """A class for schematic mapping data frames into neuroglancer states.
    Parameters
    ----------
    base_state : str, optional
        Neuroglancer json state. This is set before all
        layers are added from other arguments. Optional,
        default is None.
    dataset_name : str or None, optional
        Dataset name to populate image and segmentation layers from the InfoService. Default is None.
    segmentation_type : 'graphene' or 'flat', optional
        If dataset_name is used, specifies whether to take the flat or graph segmentation. Default is 'graphene'.
    image_layer_name : str, optional
        If dataset_name is used, defines the image layer name. Default is 'img'. Will not override explicit setting from image_sources.
    seg_layer_name : str, optional
        If dataset_name is used, defines the segmentation layer name. Default is 'seg'. Will not override explicit setting from seg_sources.
    image_sources : dict, optional
        Dict where keys are layer names and values are
        neuroglancer image sources, by default {}
    seg_sources : dict, optional
        Dict where keys are layer names and values are
        neuroglancer segmentation sources, by default {}
    selected_ids : dict, optional
        Dict where keys are segmentation layer names and
        values are an iterable of dataframe column names.
        Object root ids from these columns are added to the
        selected ids list in the segmentation layer. By default {}
    point_annotations : dict, optional
        Dict where the keys define annotation layer names and the values
        are a collection of column names to use as a source data for points
        in that annotation layer.
        By default {}
    line_annotations : dict, optional
        Dict where the keys define annotation layer names and the values
        are a collection of column name 2-tuples to use as a source for line annotatons. 
        By default {}
    sphere_annotations : dict, optional
        Dict where keys are annotation layer names and values are a collection of
        (center, radius) 2-tuples of column names for getting the source data.
        By default {}
    resolution : list, optional
        Numpy array for voxel resolution, by default [4,4,40]
    fixed_selection : dict, optional
        Dict where keys are segmentation layers and values are
        a collection of object ids to make selected for all dataframes.
        By default {}
    linked_selections: dict, optional
        Dict keyed by annotation layer name, with an entry that is a dict with keys 
        'seg_layer' and 'data' that point to the segmentation layer name and the data column, respectively.
    url_prefix : str, optional
        Default neuroglancer prefix to use, by default None.
    """

    def __init__(
        self,
        image_layers=[],
        segmentation_layers=[],
        dataset_name=None,
        segmentation_type='graphene',
        image_kws={},
        segmentation_kws={},
        client=None,
        annotation_layers=[],
        base_state=None,
        url_prefix=None,
        resolution=[4, 4, 40],
    ):
        if dataset_name is not None:
            il, sl = sources_from_client(dataset_name,
                                         segmentation_type=segmentation_type,
                                         image_kws=image_kws,
                                         segmentation_kws=segmentation_kws,
                                         client=client)
        else:
            il = None
            sl = None

        self._base_state = base_state

        if isinstance(image_layers, ImageLayerConfig):
            image_layers = [image_layers]
        if il is not None:
            image_layers.append(il)
        self._image_layers = image_layers

        if isinstance(segmentation_layers, SegmentationLayerConfig):
            segmentation_layers = [segmentation_layers]
        if sl is not None:
            segmentation_layers.append(sl)
        self._segmentation_layers = segmentation_layers

        if isinstance(annotation_layers, AnnotationLayerConfig):
            annotation_layers = [annotation_layers]
        self._annotation_layers = annotation_layers

        self._resolution = resolution
        self._url_prefix = url_prefix

    def _reset_state(self, base_state=None):
        """
        Resets the neuroglancer state status to a default viewer.
        """
        if base_state is None:
            base_state = self._base_state
        self._temp_viewer = EasyViewer()
        self._temp_viewer.set_state(base_state)

    def initialize_state(self, base_state=None):
        """Generate a new Neuroglancer state with layers as needed for the schema.

        Parameters
        ----------
        base_state : str, optional
            Optional initial state to build on, described by its JSON. By default None.
        """
        self._reset_state(base_state)
        self._temp_viewer.set_resolution(self._resolution)
        self._temp_viewer.set_view_options()

    def render_state(self, data=None, base_state=None, return_as='url', static_content_source=default_static_content_source,
                     url_prefix=None, link_text='Neuroglancer Link'):
        """Build a Neuroglancer state out of a DataFrame.

        Parameters
        ----------
        data : pandas.DataFrame, optional
            DataFrame to use as a point source. By default None, for which
            it will return only the base_state and any fixed values.
        base_state : str, optional
            Initial state to build on, expressed as Neuroglancer JSON. By default None
        return_as : ['url', 'viewer', 'html', 'json'], optional
            Choice of output types. Note that if a viewer is returned, the state is not reset.
            By default 'url'
        static_content_source : str, optional
            Sets the neuroglancer web site source to use for a viewer, if a viewer is returned.
            Optional, default is None. If none is set, uses the default value from neuroglancer_annotation_ui.utils.
        url_prefix : str, optional
            Neuroglancer URL prefix to use. By default None, for which it will open with the
            class default.
        link_text : str, optional
            Text to use for the link when returning as html, by default 'Neuroglancer Link'

        Returns
        -------
        string or neuroglancer.Viewer
            A link to or viewer for a Neuroglancer state with layers, annotations, and selected objects determined by the data.
        """
        if base_state is None:
            base_state = self._base_state
        self.initialize_state(base_state=base_state)

        if url_prefix is None:
            url_prefix = self._url_prefix

        self._render_layers(data)

        if return_as == 'viewer':
            if static_content_source is not None:
                set_static_content_source(static_content_source)
            return self.viewer
        elif return_as == 'url':
            out = self._temp_viewer.as_url(prefix=url_prefix)
            self.initialize_state()
            return out
        elif return_as == 'html':
            out = HTML(self._temp_viewer.as_url(
                prefix=url_prefix, as_html=True, link_text=link_text))
            self.initialize_state()
            return out
        elif return_as == 'dict':
            out = self._temp_viewer.state.to_json()
            self.initialize_state()
            return out
        elif return_as == 'json':
            from json import dumps
            out = self._temp_viewer.state.to_json()
            self.initialize_state()
            return dumps(out)
        else:
            raise ValueError('No appropriate return type selected')

    def _render_layers(self, data):
        for img_layer in self._image_layers:
            img_layer._render_layer(self._temp_viewer, data)

        for seg_layer in self._segmentation_layers:
            seg_layer._render_layer(self._temp_viewer, data)

        for anno_layer in self._annotation_layers:
            anno_layer._render_layer(self._temp_viewer, data)

    @property
    def viewer(self):
        return self._temp_viewer


class ChainedStateBuilder():
    def __init__(self, statebuilders):
        """Builds a collection of states that sequentially add annotations based on a sequence of dataframes.

        Parameters
        ----------
        statebuilders : list
            List of DataStateBuilders, in same order as dataframes will be passed
        """
        self._statebuilders = statebuilders
        if len(self._statebuilders) == 0:
            raise ValueError('Must have at least one statebuilder')

    def render_state(self, data_list=None, base_state=None, return_as='url', url_prefix=None):
        """Generate a single neuroglancer state by addatively applying an ordered collection of
        dataframes to an collection of StateBuilder renders.
        Parameters
            data_list : Collection of DataFrame. The order must match the order of StateBuilders
                        contained in the class on creation.
            base_state : JSON neuroglancer state (optional, default is None).
                         Used as a base state for adding everything else to.
            return_as: ['url', 'viewer', 'html', 'json']. optional, default='url'.
                       Sets how the state is returned. Note that if a viewer is returned,
                       the state is not reset to default.
            url_prefix: string, optional (default=None). Overrides the default neuroglancer url for url generation.
        """
        if data_list is None:
            data_list = len(self._statebuilders) * [None]

        if len(data_list) != len(self._statebuilders):
            raise ValueError('Must have as many dataframes as statebuilders')

        temp_state = base_state
        for builder, data in zip(self._statebuilders[:-1], data_list[:-1]):
            temp_state = builder.render_state(data=data,
                                              base_state=temp_state,
                                              return_as='json')
        last_builder = self._statebuilders[-1]
        return last_builder.render_state(data=data_list[-1],
                                         base_state=temp_state,
                                         return_as=return_as,
                                         url_prefix=url_prefix)


def sources_from_client(dataset_name, segmentation_type='graphene', image_kws={}, segmentation_kws={}, client=None):
    """Generate an Image and Segmentation source from a dataset name.

    Parameters
    ----------
    dataset_name : str
        Dataset name for client
    segmentation_type : 'graphene' or 'flat', optional
        Which segmentation type for try first, graphene or flat. It will fall back to the other if not found. By default 'graphene'
    image_kws : dict, optional
        Keyword arguments for an ImageLayerConfig (other than source), by default {}
    segmentation_kws : dict, optional
        Keyword arguments for a SegmentationLayerConfig (other than source), by default {}
    client : InfoClient or None, optional
        Predefined info client for lookup

    Returns
    -------
    ImageLayerConfig
        Config for an image layer in the statebuilder 
    SegmentationLayerConfig
        Config for a segmentation layer in the statebuilder
    """

    if client is None:
        client = FrameworkClient(dataset_name=dataset_name)

    image_source = client.info.image_source(format_for='neuroglancer')
    if segmentation_type == "graphene":
        seg_source = client.info.graphene_source(format_for='neuroglancer')
        if seg_source is None:
            seg_source = client.info.flat_segmentation_source(
                format_for='neuroglancer')
    else:
        seg_source = client.info.flat_segmentation_source(
            format_for='neuroglancer')
        if seg_source is None:
            seg_source = client.info.graphene_source(format_for='neuroglancer')

    image_layer = ImageLayerConfig(image_source, *image_kws)
    seg_layer = SegmentationLayerConfig(seg_source, *segmentation_kws)
    return image_layer, seg_layer

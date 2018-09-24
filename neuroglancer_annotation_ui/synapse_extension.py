from neuroglancer_annotation_ui.extension_core import check_layer, AnnotationExtensionBase
from neuroglancer_annotation_ui.ngl_rendering import SchemaRenderer
from neuroglancer_annotation_ui.annotation import point_annotation, \
                                                  line_annotation
from emannotationschemas.synapse import SynapseSchema

class SynapseSchemaWithRule(SynapseSchema):
    @staticmethod
    def render_rule():
        return {'line': {'pre': [('pre_pt', 'ctr_pt')],
                         'post': [('post_pt', 'ctr_pt')]},
                'point': {'syn': ['ctr_pt']}
                }

class SynapseExtension(AnnotationExtensionBase):
    def __init__(self, easy_viewer, annotation_client=None):
        super(SynapseExtension, self).__init__(easy_viewer, annotation_client)
        self.ngl_renderer = {'synapses':SchemaRenderer(SynapseSchemaWithRule)}
        self.allowed_layers = ['synapses']

        self.color_map = {'synapses': '#cccccc',
                          'synapses_pre': '#ff0000',
                          'synapses_post': '#00ffff',
                          }
        self.message_dict = {'pre_pt': 'presynaptic point',
                             'post_pt': 'postsynaptic point',
                             'ctr_pt': 'synapse'}
        self.layer_dict = {'pre_pt': 'synapses_pre',
                           'post_pt': 'synapses_post',
                           'ctr_pt': 'synapses'}
        self.render_map = {'pre':'synapses_pre',
                           'post':'synapses_post',
                           'syn':'synapses'}

        self.create_synapse_layers(None)
        self.synapse_points = {'pre_pt': None, 'post_pt': None, 'ctr_pt': None}
 

    @staticmethod
    def _default_key_bindings():
        bindings = {
            'update_presynaptic_point': 'shift+keyq',
            'update_synapse': 'shift+keyw',
            'update_postsynaptic_point': 'shift+keye',
            'create_synapse_layers': 'shift+control+keys',
            'clear_segment': 'shift+keyv'}
        return bindings

    @staticmethod
    def _defined_layers():
        return ['synapses_pre', 'synapses_post', 'synapses']

    def create_synapse_layers(self, s):
        for layer in self._defined_layers():
            self.viewer.add_annotation_layer(layer,
                                             color=self.color_map[layer])

    @check_layer()
    def update_presynaptic_point(self, s):
        self.update_synapse_points('pre_pt', s)

    @check_layer()
    def update_postsynaptic_point(self, s):
        self.update_synapse_points('post_pt', s)

    def update_synapse_points(self, point_type, s):

        if (point_type == 'pre_pt') or (point_type == 'post_pt'):
            if self.synapse_points[point_type] is None:
                message = 'Assigned {}'.format(self.message_dict[point_type])
            else:
                self.viewer.remove_annotation(self.layer_dict[point_type],
                                              self.synapse_points[point_type].id)
                message = 'Re-assigned {}'.format(self.message_dict[point_type])

            self.synapse_points[point_type] = self.make_synapse_point(s)
            self.viewer.add_annotation( self.layer_dict[point_type],
                                 [self.synapse_points[point_type]] )
            self.viewer.update_message( message)
        else:
            message = 'Assigned {}'.format(self.message_dict[point_type])
            self.synapse_points[point_type] = self.make_synapse_point(s)
            self.viewer.update_message( message)

    @check_layer()
    def update_synapse( self, s ):
        if (self.synapse_points['pre_pt'] is None) or \
                    (self.synapse_points['post_pt'] is None):
            self.viewer.update_message("Pre and Post targets must be defined before \
                                        adding a synapse!")
            return

        self.update_synapse_points( 'ctr_pt', s )
        synapse_data = self.format_synapse_data()

        viewer_ids = self.ngl_renderer['synapses'](
                          self.viewer,
                          synapse_data,
                          layermap=self.render_map,
                          replace_annotations={'synapses_pre':self.synapse_points['pre_pt'].id,
                                               'synapses_post':self.synapse_points['post_pt'].id}
                          )
        self.clear_segment()

        if self.annotation_client is not None:
            annotation_id = self._post_data(synapse_data, 'synapse')
            id_description = '{}_{}'.format(self.db_tables['synapse'], annotation_id[0])
            self.viewer.update_description(viewer_ids, id_description)
            self._update_map_id( viewer_ids, id_description )

    def _post_data(self, synapse_data, table_name):
        response = self.annotation_client.post_annotation(self.db_tables[table_name], [synapse_data])
        return response

    def make_synapse_point( self, s):
        pos = self.viewer.get_mouse_coordinates(s)
        if pos is not None:
            return point_annotation(pos)
        else:
            return None

    def format_synapse_data(self):
        return {'type':'synapse',
                'pre_pt':{'position':[int(x) for x in self.synapse_points['pre_pt'].point]},
                'ctr_pt':{'position':[int(x) for x in self.synapse_points['ctr_pt'].point]},
                'post_pt':{'position':[int(x) for x in self.synapse_points['post_pt'].point]}}

    @check_layer()
    def clear_segment(self, s=None, update_message = True):
        for pt_type, point in self.synapse_points.items():
            if point is not None:
                self.viewer.remove_annotation(self.layer_dict[pt_type], point.id)

        self.synapse_points = {'pre_pt':None, 'post_pt':None, 'ctr_pt':None}
        if update_message:
            self.viewer.update_message('No active synapse ')

    @check_layer()
    def _delete_annotation(self, ngl_id ):
        anno_id = self.get_anno_id(ngl_id)
        ae_type, ae_id = self.parse_anno_id(anno_id, self.db_tables['synapse'])
        try:
            self.annotation_client.delete_annotation(annotation_type=self.db_tables['synapse'],
                                                     oid=ae_id)
        except:
            self.viewer.update_message('AnnotationClient could not delete annotation!')
            return
        self.remove_associated_annotations(anno_id)
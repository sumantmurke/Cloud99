from glanceclient.v2 import client as glance_client
from glanceclient.exc import ClientException

class GlanceHealth(object):
    def __init__(self, keystone_instance):
        """
        Find the image endpoint
        """
        glance_endpoint = keystone_instance.keystone_endpoint_find(service_type='image')
        self.glanceclient = glance_client.Client(glance_endpoint, token=keystone_instance.keystone_return_authtoken())
    
    def glance_image_list(self):
        try:
            image_list = self.glanceclient.images.list()
        except (ClientException, Exception) as e:
            return (404, e.message, [])
        return (200, "success", image_list)
        

import os
import re
import json
import logging
import hashlib

from datetime import datetime as dt

from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client


'''
This is Python 2.7 code for openstack client to deliver images to openstack's glance from folder in automatic way
The jenkins job can be configured to start this code in someday and do it's update/delivery process
But you have to configure ansible hosts file to target your host

Functional - when you upload images that have to be created or updated on openstack's glance
you put images on host all images of a raw format from folder will be processed to code.

Nice to do it with jenkins so you don't want to bother about doing it by yourself.
Deleting images is not gonna be implemented yet beacause we don't need to delete images.
But mb I will add this method too in future and rename too.

+Also when image is gonna be updated - we need to check if name already exists. 
+If it's already in glance we need to check checksum - if it is equal - nothing to do
+else - old one rename by adding _old (mb also add '_after_date' is a good idea?)
and then upload new one

Take regions info from json file then cycle throw it and do checking ethalon dir vs what is
in glance and run methods
'''


__author__ = "Michael Salamakha | WolfusFlow"

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

class Image_Delivery:

    def __init__(self):

        self.ethalon_image_list = self.get_images_from_folder()

    def get_images_from_folder(self):
        image_list = []
        [image_list.append(item) for item in os.listdir('.') if re.search(r'.*(.raw)', item)]
        return image_list

    def connect_to_region(self, *args, **kwargs):
        
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(
            auth_url=kwargs['auth_url'], 
            username=kwargs['username'], 
            password=kwargs['password'], 
            project_name=kwargs['project_name'], #project_id
            project_domain_name=kwargs['project_domain_name'], 
            user_domain_name=kwargs['user_domain_name'], 
        )
        try:
            new_session = session.Session(auth=auth, verify=False)
            return new_session
        except keystoneauth1.exceptions.auth.MissingAuthMethods, keystoneauth1.exceptions.auth.AuthorizationFailure as error:
            logging.error('Error while creating keystone session: {}'.format(error))


    def calculate_md5_hash(self, filename):
        hash_md5 = hashlib.md5()
        
        with open(filename, 'rb') as f:
            for chunk in iter(lambda : f.read(4096), b''):
                hash_md5.update(chunk)
       
        return hash_md5.hexdigest() 

    def upload_new_image(self, new_image, new_image_name, glance):
        image = glance.images.create(name=new_image_name, disk_format='raw', container_format='bare')
        glance.images.upload(image.id, open(new_image, 'rb'))
       # image = glance.images.create(name="newImage")
       # glance.image.upload(image.id, open('/path/to/image.raw', 'rb'))


    def update_image_to_old(self, image, glance):
        try:
            updated_date = dt.now().strftime('%Y-%m-%d_%H:%M:%S')
            glance.images.update(image.id, name='{}_old_after_{}'.format(image.name, updated_date))
        except glance.common.exception.ImageNotFound as error:
            logging.error('Image was not found: {}'.format(error))


    def check_image_type(self, image_to_check, image_checksum_to_check, glance_images):
        for image in glance_images:
            if image.name == image_to_check:
                if image.checksum == image_checksum_to_check:
                    return 'duplicate', None
                elif image.checksum != image_checksum_to_check:
                    return 'new_version', image

        return 'new_image', None

# If checksum is equal and name is different - mb add method for rename

if __name__ == '__main__':
    image_delivery = Image_Delivery()
    with open('regions.json') as regions_file:
        regions_data = json.load(regions_file)
        for region_key, region_value in regions_data.items():
            for alf in regions_data[region_key]:
                current_session = image_delivery.connect_to_region(region=alf['region'], username=alf['username'],\
password=alf['password'], auth_url=alf['auth_url'], project_name=alf['project_name'],\
project_domain_name=alf['project_domain_name'], user_domain_name=alf['user_domain_name'])
                
                glance = None
                if current_session:
                    try:
                        glance = Client('2', session=current_session)
                        glance_images = list(glance.images.list())
                    except glance.common.exception.AuthBadRequest, glance.common.exception.ClientConnectionError as error:
                        logging.error('Error while connecting to glance {}'.format(error))
                    
                if glance:

                    for image in image_delivery.ethalon_image_list:
                        image_name = unicode(image.split('.')[0], 'utf-8')
                        image_checksum = unicode(image_delivery.calculate_md5_hash(image), 'utf-8')

                        type_of_image, existing_image_to_change = image_delivery.check_image_type(image_name, image_checksum, glance_images)

                        logging.info('RESULT::: ', type_of_image, '  ', existing_image_to_change)
                        if type_of_image == 'duplicate':
                            logging.info('duplicate')
                            continue
                        elif type_of_image == 'new_version':
                            logging.info('new_version')
                            image_delivery.update_image_to_old(existing_image_to_change, glance)
                            image_delivery.upload_new_image(image, image_name, glance)
                        elif type_of_image == 'new_image':
                            logging.info('upload_new_image')
                            image_delivery.upload_new_image(image, image_name, glance)

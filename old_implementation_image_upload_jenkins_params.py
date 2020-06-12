import os
import re
import hashlib
import argparse

from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client


'''
It is an old implementation with print outputs and arguments send to code at executions
Main Idea was to send arguments throw jenkins job.
The latest version have just this name - "image_upload.py"

TODO make a doc info
functional - when you upload images that have to be created or updated
you put images on host than you need to specify what images you want to upload/update
main idea is to do it with jenkins - getting list of items from directory 
and then send them as an argument to program execution.
Work with this list and upload/update only images with this names.
Del is not gonna be implemented yet bacause we don't delete images.

+Also when image is gonna be updated - we need to check if name already exists. 
+If it's already in glance we need to check checksum - if it is equal - nothing to do
+else - old one rename by adding _old_after_date (is it good?) and then upload new one

The region where image have to be uploaded need to be choosen from jenkins and send
as argument.

keystone info should be as a parameter in executing of a programm or will be set
with env var?

Make auth to be filled with params from arg_parse

Ansible connection is ready need to add params to connect via jenkins and do things
'''

__author__ = "Michael Salamakha | WolfusFlow"

class Image_Delivery:

    def __init__(self):

        parser  = argparse.ArgumentParser()
        parser.add_argument('--region', help='Region(s) Name')
        parser.add_argument('--image', help='Image(s) List')
        parser.add_argument('--username', help='Username for auth')
        parser.add_argument('--password', help='User password for auth')
        parser.add_argument('--auth_url', help='Auth url')
        parser.add_argument('--project_name', help='porject_name')
        parser.add_argument('--project_domain_name', help='Project\'s domain name')
        parser.add_argument('--user_domain_name', help='User\'s domain name')
        args = parser.parse_args()
        print(args)

        if args.region == None:
            raise Exception('Region didn\'t input')
        else:
            print('region: ', args.region)
            self.regions = args.region
        if args.image == None:
            raise Exception('Image(s) didn\'t input')
        else:
            print(args.image)
            print(list(args.image.split(',')))
            self.new_images = list(args.image.split(','))

        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(
            auth_url=args.auth_url, 
            username=args.username, 
            password=args.password, 
            project_name=args.project_name, 
            project_domain_name=args.project_domain_name, 
            user_domain_name=args.user_domain_name, 
        )
        self.session = session.Session(auth=auth, verify=False)

        self.glance = Client('2', session=self.session)

        self.existing_images = list(self.glance.images.list())


    def calculate_md5_hash(self, filename):
        hash_md5 = hashlib.md5()
        
        with open(filename, 'rb') as f:
            for chunk in iter(lambda : f.read(4096), b''):
                hash_md5.update(chunk)
       
        return hash_md5.hexdigest() 

    def create_new_image(self, new_image, new_image_name):
        image = self.glance.images.create(name=new_image_name, disk_format='raw', container_format='bare')
        self.glance.images.upload(image.id, open(new_image, 'rb'))
       # image = glance.images.create(name="newImage")
       # glance.image.upload(image.id, open('/path/to/image.raw', 'rb'))


    def update_image_to_old(self, image):
        self.glance.images.update(image.id, name='{}_old'.format(image.name))

    def check_existance(self, new_image_name, new_image_checksum):
        for existing_image in self.existing_images:
            print(existing_image.name)
            print(new_image_name)
            print(existing_image.checksum)
            print(new_image_checksum)
            print('---------')
            if existing_image.name == new_image_name:
               if existing_image.checksum == new_image_checksum:
                   return 'duplicate', None 
               elif existing_image.checksum != new_image_checksum:
                   return 'new_version', existing_image

        return 'new_image', None

# If checksum is equal and name is different - mb add method for rename>

if __name__ == '__main__':
    image_delivery = Image_Delivery()
    for new_image in image_delivery.new_images:
        print('------')
        new_image_name = unicode(new_image.split('.')[0], 'utf-8')
        new_image_checksum = unicode(image_delivery.calculate_md5_hash(new_image), 'utf-8')

        type_of_image, existing_image_to_change = image_delivery.check_existance(new_image_name, new_image_checksum)

        if type_of_image == 'duplicate':
            print('duplicate')
            continue
        elif type_of_image == 'new_version':
            print('new_version')
            image_delivery.update_image_to_old(existing_image_to_change)
            image_delivery.create_new_image(new_image, new_image_name) 
        elif type_of_image == 'new_image':
            print('create_new_image')
            image_delivery.create_new_image(new_image, new_image_name)


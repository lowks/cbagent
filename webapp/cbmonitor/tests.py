import json
from uuid import uuid4
from random import randint, choice

from django.test import TestCase
from django.test.client import RequestFactory
from django.core.exceptions import ObjectDoesNotExist

import views
import rest_api
from models import Cluster, Server, Bucket

uhex = lambda: uuid4().hex


class BasicTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_index(self):
        request = self.factory.get('/')
        response = views.index(request)
        self.assertEqual(response.status_code, 200)


class ApiTest(TestCase):

    fixtures = ["bucket_type.json", "testdata.json"]

    def setUp(self):
        self.factory = RequestFactory()

    def add_item(self, item, params):
        """Add new cluster/server/bucket"""
        request = self.factory.post("/add_" + item, params)
        response = rest_api.dispatcher(request, path="add_" + item)
        return response

    def delete_item(self, item, params):
        """Add new cluster/server/bucket"""
        request = self.factory.post("/delete_" + item, params)
        response = rest_api.dispatcher(request, path="delete_" + item)
        return response

    def verify_valid_response(self, response):
        self.assertEqual(response.content, "Success")
        self.assertEqual(response.status_code, 200)

    def verify_missing_parameter(self, response):
        self.assertEqual(response.content, "Missing Parameter")
        self.assertEqual(response.status_code, 400)

    def verify_duplicate(self, response):
        self.assertEqual(response.content, "Duplicate")
        self.assertEqual(response.status_code, 400)

    def verify_bad_parent(self, response):
        self.assertEqual(response.content, "Bad Parent")
        self.assertEqual(response.status_code, 400)

    def verify_bad_parameter(self, response):
        self.assertEqual(response.content, "Bad Parameter")
        self.assertEqual(response.status_code, 400)

    def verify_valid_json(self, response):
        json.loads(response.content)
        self.assertEqual(response.status_code, 200)

    def test_add_cluster(self):
        """Adding new cluster with full set of params"""
        params = {"name": uhex(), "description": uhex()}
        response = self.add_item("cluster", params)

        # Verify response
        self.verify_valid_response(response)

        # Verify persistence
        cluster = Cluster.objects.get(name=params["name"])
        self.assertEqual(cluster.description, params["description"])

    def test_add_cluster_wo_description(self):
        """Adding new cluster with missing optional params"""
        params = {"name": uhex()}
        response = self.add_item("cluster", params)

        # Verify response
        self.verify_valid_response(response)

        # Verify persistence
        cluster = Cluster.objects.get(name=params["name"])
        self.assertEqual(cluster.description, "")

    def test_add_cluster_duplicate(self):
        """Adding duplicate cluster"""
        params = {"name": uhex()}

        # Verify response
        response = self.add_item("cluster", params)
        self.verify_valid_response(response)

        response = self.add_item("cluster", params)
        self.verify_duplicate(response)

    def test_add_cluster_wo_name(self):
        """Adding new cluster with missing mandatory params"""
        params = {"description": uhex()}
        response = self.add_item("cluster", params)

        # Verify response
        self.verify_missing_parameter(response)

    def test_add_server(self):
        """Adding new server with full set of params"""
        cluster = uhex()
        self.add_item("cluster", {"name": cluster})

        params = {
            "cluster": cluster, "address": uhex(),
            "rest_username": uhex(), "rest_password": uhex(),
            "ssh_username": uhex(), "ssh_password": uhex(), "ssh_key": uhex(),
            "description": uhex()
        }

        response = self.add_item("server", params)

        # Verify response
        self.verify_valid_response(response)

        # Verify persistence
        server = Server.objects.get(address=params["address"])
        self.assertEqual(server.cluster.name, cluster)

    def test_add_server_to_wrong_cluster(self):
        """Adding new server with wrong cluster parameter"""
        params = {
            "cluster": uhex(), "address": uhex(),
            "rest_username": uhex(), "rest_password": uhex(),
            "ssh_username": uhex(), "ssh_password": uhex(), "ssh_key": uhex(),
            "description": uhex()
        }

        response = self.add_item("server", params)

        # Verify response
        self.verify_bad_parent(response)

    def test_add_server_wo_ssh_credentials(self):
        """Adding new server w/o SSH password and key"""
        cluster = uhex()
        self.add_item("cluster", {"name": cluster})

        params = {
            "cluster": cluster, "address": uhex(),
            "rest_username": uhex(), "rest_password": uhex(),
            "ssh_username": uhex(),
            "description": uhex()
        }

        response = self.add_item("server", params)

        # Verify response
        self.verify_missing_parameter(response)

    def test_add_bucket(self):
        """Adding new bucket with full set of params"""

        cluster = uhex()
        self.add_item("cluster", {"name": cluster})

        server = uhex()
        params = {
            "cluster": cluster, "address": server,
            "rest_username": uhex(), "rest_password": uhex(),
            "ssh_username": uhex(), "ssh_password": uhex()
        }
        self.add_item("server", params)

        params = {
            "server": server,
            "name": uhex(), "type": choice(("Couchbase", "Memcached")),
            "port": randint(1, 65535), "password": uhex()
        }
        response = self.add_item("bucket", params)

        # Verify response
        self.verify_valid_response(response)

        # Verify persistence
        bucket = Bucket.objects.get(name=params["name"])
        self.assertEqual(bucket.server.cluster.name, cluster)

    def test_add_bucket_with_wrong_port(self):
        """Adding new bucket with wrong type of port parameter"""
        cluster = uhex()
        self.add_item("cluster", {"name": cluster})

        server = uhex()
        params = {
            "cluster": cluster, "address": server,
            "rest_username": uhex(), "rest_password": uhex(),
            "ssh_username": uhex(), "ssh_password": uhex()
        }
        self.add_item("server", params)

        params = {
            "server": server,
            "name": uhex(), "type": choice(("Couchbase", "Memcached")),
            "port": uhex(), "password": uhex()
        }
        response = self.add_item("bucket", params)

        # Verify response
        self.verify_bad_parameter(response)

    def test_add_bucket_with_wrong_type(self):
        """Adding new bucket with wrong type parameter"""
        cluster = uhex()
        self.add_item("cluster", {"name": cluster})

        server = uhex()
        params = {
            "cluster": cluster, "address": server,
            "rest_username": uhex(), "rest_password": uhex(),
            "ssh_username": uhex(), "ssh_password": uhex()
        }
        self.add_item("server", params)

        params = {
            "server": server,
            "name": uhex(), "type": uhex(),
            "port": randint(1, 65535), "password": uhex()
        }
        response = self.add_item("bucket", params)

        # Verify response
        self.verify_bad_parent(response)

    def test_remove_cluster(self):
        """Removing existing cluster"""
        cluster = uhex()
        self.add_item("cluster", {"name": cluster})

        response = self.delete_item("cluster", {"name": cluster})

        # Verify response
        self.verify_valid_response(response)

        # Verify persistence
        self.assertRaises(ObjectDoesNotExist, Cluster.objects.get,
                          name=cluster)

    def test_remove_server(self):
        """Removing existing cluster"""
        cluster = uhex()
        self.add_item("cluster", {"name": cluster})
        params = {
            "cluster": cluster, "address": uhex(),
            "rest_username": uhex(), "rest_password": uhex(),
            "ssh_username": uhex(), "ssh_password": uhex(), "ssh_key": uhex(),
            "description": uhex()
        }
        self.add_item("server", params)

        response = self.delete_item("server", {"address": params["address"]})

        # Verify response
        self.verify_valid_response(response)

        # Verify persistence
        self.assertRaises(ObjectDoesNotExist, Server.objects.get,
                          address=params["address"])

    def test_remove_bucket(self):
        """Removing existing cluster"""
        cluster = uhex()
        self.add_item("cluster", {"name": cluster})
        server = uhex()
        params = {
            "cluster": cluster, "address": server,
            "rest_username": uhex(), "rest_password": uhex(),
            "ssh_username": uhex(), "ssh_password": uhex(), "ssh_key": uhex(),
            "description": uhex()
        }
        self.add_item("server", params)

        params = {
            "server": params["address"],
            "name": uhex(), "type": choice(("Couchbase", "Memcached")),
            "port": randint(1, 65535), "password": uhex()
        }
        self.add_item("bucket", params)

        response = self.delete_item("bucket",
                                    {"name": params["name"], "server": server})

        # Verify response
        self.verify_valid_response(response)

        # Verify persistence
        self.assertRaises(ObjectDoesNotExist, Bucket.objects.get,
                          name=params["name"], server=server)

    def test_get_tree_data(self):
        request = self.factory.get("/get_tree_data")
        response = rest_api.dispatcher(request, path="get_tree_data")

        self.verify_valid_json(response)
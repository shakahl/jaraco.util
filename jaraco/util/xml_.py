# -*- coding: UTF-8 -*-

from __future__ import absolute_import

"""
`xml`

Classes and routines for supporting xml processing with minidom.

Copyright © 2004,2011 Jason R. Coombs
"""

import itertools
import logging
import time
import datetime
import xml.dom.minidom
from xml.parsers.expat import ExpatError
import string

from jaraco.util import reverse_lists, replace_list

log = logging.getLogger(__name__)

quote_substitutions = (
	('"','&quot;'),
	# leave out this substitution for now
	#("'",'&apos;'),
)
reverse_substitutions = reverse_lists(quote_substitutions)

def to_xml_quoted_string(s):
	return replace_list(s, quote_substitutions)

def from_xml_quoted_string(s):
	return replace_list(s, reverse_substitutions)

def get_xml_representation(value):
	"Get the appropriate XML representation for value"
	try:
		value = value.XMLRepr
	except AttributeError: pass
	# want to get the best precision for a float
	if isinstance(value, float):
		value = repr(value)
	else:
		value = to_xml_quoted_string(value)
	return value

def parse_xml_time(xml_time):
	"Take a time string in XML format and return the value as a datetime object"
	pattern = '%Y-%m-%dT%H:%M:%S'
	return datetime.datetime(*time.strptime(xml_time, pattern)[:6])

class XMLObject(dict):
	xml = xml.dom.minidom.getDOMImplementation()

	def xml_repr(self):
		return self.getFragment().toxml()

	@property
	def _node_name(self):
		return self.encode_xml_name(self.__class__.__name__)

	def get_attributes(self):
		return itertools.imap(self.encode_attribute, self.iteritems())

	def encode_attribute(self, attr):
		name, val = attr
		if type(val) in (datetime, date, time):
			val = val.isoformat()
		return (self.encode_xml_name(name), str(val))

	def encode_xml_name(self, n):
		return string.join(self.encode_xml_name_chars(n), '')

	valid_chars = (
		list(range(0x30, 0x3A)) +
		list(range(0x41, 0x5B)) +
		list(range(0x61, 0x7B)) + [ord('-'), ord('_'), ord('.')]
		)
	def encode_xml_name_chars(self, n):
		for c in n:
			if ord(c) in self.valid_chars:
				yield c
			else:
				yield '_x%04x_' % ord(c)

	def get_fragment(self):
		doc = self.xml.createDocument(None, 'root', None)
		element = doc.createElement(self._node_name)
		for attr in self.get_attributes():
			element.setAttribute(*attr)
		return element

def load_xml_objects(filename, object_module):
	doc = xml.dom.minidom.parse(open(filename, 'r'))
	return get_xml_objects(doc.getElementsByTagName('*'), object_module)

def get_xml_objects(node_set, object_module):
	for object_node in node_set:
		try:
			object_class = getattr(object_module, object_node.nodeName)
			yield object_class(object_node.attributes.items())
		except AttributeError: pass # class does not exist

def get_children_by_type(node, type):
	return filter(lambda n: n.nodeType == type, node.childNodes)

def get_child_elements(node):
	return get_children_by_type(node, node.ELEMENT_NODE)

def save_xml_objects(filename, objects, root = 'root'):
	with open(filename, 'a+') as f:
		try:
			doc = xml.dom.minidom.parse(f)
		except ExpatError:
			DOM = xml.dom.minidom.getDOMImplementation()
			doc = DOM.createDocument(None, root, None)
		xml_nodes = map(lambda o: o.getFragment(), objects)
		map(doc.documentElement.appendChild, xml_nodes)
		f.seek(0)
		f.write(doc.toprettyxml())

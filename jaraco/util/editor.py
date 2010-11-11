import tempfile
import os
import sys
import subprocess

class EditableFile(object):
	"""
	EditableFile saves some data to a temporary file, launches a
	platform editor for interactive editing, and then reloads the data,
	setting .changed to True if the data was edited.
	
	e.g.
	
	x = EditableFile('foo')
	x.edit()
	if x.changed:
		print x.data
		
	The EDITOR environment variable can define which executable to use
	(also XML_EDITOR if the content-type to edit includes 'xml'). If no
	EDITOR is defined, defaults to 'notepad' on Windows and 'edit' on
	other platforms.
	"""
	def __init__(self, data=None):
		self.data = data

	def __enter__(self):
		fobj, self.name = tempfile.mkstemp()
		if self.data:
			os.write(fobj, self.data)
		os.close(fobj)
		return self

	def read(self):
		with open(self.name, 'rb') as f:
			return f.read()

	def __exit__(self, *tb_info):
		os.remove(self.name)

	def edit(self, content_type='text/plain'):
		"""
		Edit the file
		"""
		self.changed = False
		with self:
			editor = self.get_editor(content_type)
			cmd = [editor, self.name]
			try:
				res = subprocess.call(cmd)
			except Exception, e:
				print("Error launching editor %(editor)s" % vars())
				print(e)
				return
			if res != 0: return
			new_data = self.read()
			if new_data != self.data:
				self.changed = True
				self.data = new_data

	@staticmethod
	def get_editor(content_type):
		"""
		Give preference to an XML_EDITOR or EDITOR defined in the
		environment. Otherwise use notepad on Windows and edit on other
		platforms.
		"""
		env_search = ['EDITOR']
		if 'xml' in content_type:
			env_search.insert(0, 'XML_EDITOR')
		default_editor = ['edit', 'notepad'][sys.platform.startswith('win32')]
		# we're going to use reduce to search the environment; the last
		#  value is the fallback (it's not looked up in the env).
		env_search.append(default_editor)
		return reduce(os.environ.get, env_search)

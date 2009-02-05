import geotrans2_lib

engine_errors = [key for key in dir(geotrans2_lib) if key.startswith('ENGINE')]

def initialize_engine():
	res = geotrans2_lib.Initialize_Engine()
	errors = [error for error in engine_errors if getattr(geotrans2_lib, error) & res]
	if errors:
		raise Exception(errors)
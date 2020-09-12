import pyinsane2
import logging

logger = logging.getLogger(__name__)


def get_scanned_image():
	requests_logger = logging.getLogger('pyinsane2')
	requests_logger.setLevel(logging.CRITICAL)
	logger.info("Initializing pyinsane2 instance")
	pyinsane2.init()
	try:
		devices = pyinsane2.get_devices()
		logger.info("%d device(s) found." % len(devices))
		assert (len(devices) > 0)
		device = devices[0]
		logger.info("I'm going to use the following scanner: %s" % (str(device)))

		pyinsane2.set_scanner_opt(device, 'resolution', [300])

		# Beware: Some scanners have "Lineart" or "Gray" as default mode
		# better set the mode everytime
		pyinsane2.set_scanner_opt(device, 'mode', ['Color'])

		# Beware: by default, some scanners only scan part of the area
		# they could scan.
		# pyinsane2.maximize_scan_area(device)
		device.options['tl-x'].value = 0
		device.options['tl-y'].value = 0
		device.options['br-x'].value = 1000
		device.options['br-y'].value = 1000

		scan_session = device.scan(multiple=False)
		try:
			while True:
				scan_session.scan.read()
		except EOFError:
			pass
		image = scan_session.images[-1]
		return image
	finally:
		logger.info("Closing pyinsane2 instance.")
		pyinsane2.exit()


if __name__ == "__main__":
	image = get_scanned_image()
	image.save("scanned.jpg", "JPEG")

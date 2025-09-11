from odoo import http
from odoo.http import request

class TrackingController(http.Controller):

    @http.route('/tracking/search', type='json', auth='user')
    def search_tracking(self, tracking_number, **kwargs):
        """
        Endpoint para buscar tracking number
        """
        try:
            tracking_model = request.env['tracking.excel']
            result = tracking_model.search_tracking(tracking_number)
            return result
        except Exception as e:
            return {'error': str(e)}
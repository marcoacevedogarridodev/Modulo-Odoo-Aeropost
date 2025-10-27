import logging
import requests
import base64
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    aerotrack = fields.Text(string='MIA Aerotrack', store=True)
    estado_pedido = fields.Html(string='Estado Pedido', compute="_compute_estado_pedido", store=True, readonly=True, sanitize=False)
    aeropost_last_sync = fields.Datetime(string='Última sincronización', readonly=True)
    partner_id = fields.Many2one(required=False)
    AEROPOST_STATE_MAPPING = {
        '18': {'estado_odoo': 'En Bodega Miami', 'estado_cliente': 'En Bodega Miami'},
        '19': {'estado_odoo': 'Preparando Envío', 'estado_cliente': 'Preparando Envío'},
        '100': {'estado_odoo': 'En Aduanas', 'estado_cliente': 'En Servicio Aduanas'},
        '110': {'estado_odoo': 'En Aduanas - En Inspección', 'estado_cliente': 'En Servicio Aduanas'},
        '120': {'estado_odoo': 'En Aduanas - Documentos', 'estado_cliente': 'En Servicio Aduanas'},
        '130': {'estado_odoo': 'En Aduanas - Documentos', 'estado_cliente': 'En Servicio Aduanas'},
        '140': {'estado_odoo': 'En Aduanas - Documentos', 'estado_cliente': 'En Servicio Aduanas'},
        '200': {'estado_odoo': 'Liberado Aduanas', 'estado_cliente': 'Liberado Aduanas'},
        '250': {'estado_odoo': 'Recibido', 'estado_cliente': 'Recepcionado Embarcador'},
        '260': {'estado_odoo': 'Transito a Chile', 'estado_cliente': 'En Transito Internacional'},
        '270': {'estado_odoo': 'Ingreso Aeropuerto', 'estado_cliente': 'Recepcionado Embarcador'},
        '280': {'estado_odoo': 'Informacion Recibida', 'estado_cliente': 'Recepcionado Embarcador'},
        '300': {'estado_odoo': 'En Entrega', 'estado_cliente': 'En Transito al Pais'},
        '310': {'estado_odoo': 'En Entrega', 'estado_cliente': 'En Transito al Pais'},
        '320': {'estado_odoo': 'En Entrega', 'estado_cliente': 'En Transito al Pais'},
        '400': {'estado_odoo': 'Entregado Courier', 'estado_cliente': 'En Transito al Pais'},
        '420': {'estado_odoo': 'Entregado Courier', 'estado_cliente': 'En Transito al Pais'},
        '500': {'estado_odoo': 'Listo Retiro', 'estado_cliente': 'En Proceso Bodega AutoPro'},
        '550': {'estado_odoo': 'Listo Retiro', 'estado_cliente': 'En Proceso Bodega AutoPro'},
        '600': {'estado_odoo': 'En Bodega MIA', 'estado_cliente': 'En Proceso Bodega AutoPro'},
        '700': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '701': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '702': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '703': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '704': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '705': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '706': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '707': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '708': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '709': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '800': {'estado_odoo': 'En Transito a Retiro', 'estado_cliente': 'En Proceso Bodega AutoPro'},
        '1000': {'estado_odoo': 'Entregado', 'estado_cliente': 'En Transito Bodega'},
        '1100': {'estado_odoo': 'Paquete Abandonado', 'estado_cliente': 'Paquete Abandonado'},
        '1110': {'estado_odoo': 'Paquete Abandonado', 'estado_cliente': 'Paquete Abandonado'},
        '1120': {'estado_odoo': 'Paquete Abandonado', 'estado_cliente': 'Paquete Abandonado'},
        '1200': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '1201': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '1202': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '1203': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '1204': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '1205': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '1206': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '1207': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '1208': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '1209': {'estado_odoo': 'No Entregado', 'estado_cliente': 'En Transito al Pais'},
        '53': {'estado_odoo': 'Vuelo Retrasado', 'estado_cliente': 'En Transito Internacional'},
    }

    def _get_aeropost_token(self):
        try:
            auth_url = "https://account.aeropost.com/auth/realms/myaccount/protocol/openid-connect/token"
            credentials = "exposervice:iWmIn2rxR0wEmciMvGeg6orRO1PcoNvL"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Basic {encoded_credentials}'}
            data = {'grant_type': 'password', 'scope': 'openid email', 'username': '105760', 'password': 'vwxk8295VW', 'gateway': 'SCL'}
            response = requests.post(auth_url, data=data, headers=headers, timeout=10)
            return response.json().get('access_token') if response.status_code == 200 else None
        except Exception:
            return None

    def _get_package_info(self, aerotrack_code):
        try:
            token = self._get_aeropost_token()
            if not token: return None
            url = f"https://apmyaccountexternal-api.aeropost.com/api/v2/packages/{aerotrack_code.strip().upper()}"
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            response = requests.get(url, headers=headers, timeout=10)
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None

    def _get_odoo_state_from_aeropost(self, aeropost_status_id):
        if not aeropost_status_id:
            return {'estado_odoo': 'Desconocido', 'estado_cliente': 'Estado no disponible'}
        return self.AEROPOST_STATE_MAPPING.get(str(aeropost_status_id), {'estado_odoo': 'En Proceso', 'estado_cliente': 'En Proceso'})

    def _get_status_color(self, estado_odoo, status_code):
        """Asignar colores específicos por código de estado"""
        status_code_str = str(status_code)
        
        color_map = {
  
            '1000': "#27ae60",
            '700': "#e74c3c", '701': "#e74c3c", '702': "#e74c3c", '703': "#e74c3c", '704': "#e74c3c",
            '705': "#e74c3c", '706': "#e74c3c", '707': "#e74c3c", '708': "#e74c3c", '709': "#e74c3c",
            '1100': "#e74c3c", '1110': "#e74c3c", '1120': "#e74c3c",
            '1200': "#e74c3c", '1201': "#e74c3c", '1202': "#e74c3c", '1203': "#e74c3c", '1204': "#e74c3c",
            '1205': "#e74c3c", '1206': "#e74c3c", '1207': "#e74c3c", '1208': "#e74c3c", '1209': "#e74c3c",
            '100': "#f39c12", '110': "#f39c12", '120': "#f39c12", '130': "#f39c12", '140': "#f39c12",
            '200': "#2ecc71", '500': "#2ecc71", '550': "#2ecc71", '600': "#2ecc71", '800': "#2ecc71",
            '250': "#3498db", '260': "#3498db", '270': "#3498db", '280': "#3498db",
            '300': "#3498db", '310': "#3498db", '320': "#3498db", '400': "#3498db", '420': "#3498db", '53': "#3498db",
            '18': "#2980b9", '19': "#2980b9",
        }

        if status_code_str in color_map:
            return color_map[status_code_str]

        estado_lower = estado_odoo.lower()
        if 'entregado' in estado_lower:
            return "#27ae60"
        elif any(x in estado_lower for x in ['no entregado', 'abandonado', 'dañado', 'destruido']):
            return "#e74c3c"
        elif 'aduanas' in estado_lower:
            return "#f39c12"
        elif any(x in estado_lower for x in ['liberado', 'listo']):
            return "#2ecc71"
        elif any(x in estado_lower for x in ['tránsito', 'entrega', 'envío', 'reparto']):
            return "#3498db"
        elif any(x in estado_lower for x in ['proceso', 'recibido', 'bodega', 'preparando']):
            return "#2980b9"

        return "#3498db"

    def _format_package_status(self, package_data):
        if not package_data:
            return "<div style='color: orange; border: 1px solid #ddd; padding: 10px; margin-bottom: 10px;'>No encontrado en AeroPost</div>"
        
        try:
            aerotrack = package_data.get('aerotrack', 'N/A')
            status_name = package_data.get('statusName', 'N/A')
            status_code = package_data.get('statusCode', 'N/A')
            last_update = package_data.get('lastUpdate', 'N/A')
            courier_tracking = package_data.get('courierTracking', 'N/A')
            estado_info = self._get_odoo_state_from_aeropost(status_code)
            estado_odoo = estado_info['estado_odoo']
            estado_cliente = estado_info['estado_cliente']
            color = self._get_status_color(estado_odoo, status_code)

            if last_update != 'N/A':
                try:
                    last_update = datetime.fromisoformat(last_update.replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M:%S')
                except:
                    pass

            return f"""
            <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; background: #f9f9f9; border-left: 5px solid {color};">
                <strong style="color: {color}; font-size: 14px;">{status_name}</strong>
                <div style="margin-top: 5px;"><strong>MIA:</strong> {aerotrack}</div>
                <div><strong>Referencia:</strong> {courier_tracking}</div>
                <div><strong>Estado Odoo:</strong> <span style="color: {color}; font-weight: bold;">{estado_odoo}</span></div>
                <div><strong>Estado Cliente:</strong> {estado_cliente}</div>
                <div><strong>Última actualización:</strong> {last_update}</div>
            </div>
            """
        except Exception as e:
            return f"<div style='color: red; border: 1px solid #ddd; padding: 10px;'>Error: {e}</div>"
    
    def get_aerotrack_codes_list(self):
        self.ensure_one()
        if not self.aerotrack: return []
        text = self.aerotrack.replace('\n', ',').replace(';', ',')
        return [code.strip().upper() for code in text.split(',') if code.strip()]

    @api.depends('aerotrack')
    def _compute_estado_pedido(self):
        for order in self:
            if not order.aerotrack:
                order.estado_pedido = "<div style='color: gray;'>Ingrese códigos MIA Aerotrack</div>"
                continue
            codes = order.get_aerotrack_codes_list()
            estados_html = []
            for code in codes:
                package_data = order._get_package_info(code)
                estados_html.append(self._format_package_status(package_data))
            order.estado_pedido = ''.join(estados_html)
            order.aeropost_last_sync = datetime.now()

    def action_find_purchase_by_reference(self):
        self.ensure_one()
        
        if not self.aerotrack:
            raise UserError("Por favor ingrese al menos un código MIA Aerotrack")
        
        codes = self.get_aerotrack_codes_list()
        if not codes:
            raise UserError("No se encontraron códigos MIA válidos")
        
        main_code = codes[0]
        package_data = self._get_package_info(main_code)
        
        if not package_data:
            raise UserError(f"No se pudo obtener información para el código MIA: {main_code}")
        
        courier_tracking = package_data.get('courierTracking')
        if not courier_tracking:
            raise UserError(f"No se encontró referencia de courier para el código MIA: {main_code}")
        
        existing_purchase_order = self.env['purchase.order'].search([
            ('partner_ref', '=', courier_tracking)
        ], limit=1)
        
        if not existing_purchase_order:
            raise UserError(f"No se encontró ningún pedido de compra existente con la referencia: {courier_tracking}")
        
        existing_order_id = existing_purchase_order.id
        aerotrack_value = self.aerotrack
        current_order_empty = (
            self.state == 'draft' and 
            not self.partner_id and 
            not self.order_line and 
            not self.partner_ref and
            len(self.get_aerotrack_codes_list()) <= 1
        )
        existing_purchase_order.write({
            'aerotrack': aerotrack_value
        })
        existing_purchase_order._compute_estado_pedido()
    
        if current_order_empty:
            try:
                current_order = self.env['purchase.order'].browse(self.id)
                if current_order.exists():
                    current_order.unlink()
            except Exception as e:
                _logger.warning(f"No se pudo eliminar el pedido vacío: {str(e)}")
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order', 
            'res_id': existing_order_id,
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'current',
        }
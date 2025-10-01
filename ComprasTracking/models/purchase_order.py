import os
import logging
import requests
import base64
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    x_aerotrack = fields.Text(
        string='MIA Aerotrack',
        store=True
    )
    x_estado_pedido = fields.Html(
        string='Estado Pedido',
        compute="_compute_estado_pedido",
        store=True,
        readonly=True,
        sanitize=False
    )
    x_aeropost_last_sync = fields.Datetime(
        string='Última Sincronización',
        readonly=True
    )

    AEROPOST_CONFIG = {
        'auth_url': 'https://account.aeropost.com',
        'api_url': 'https://apmyaccountexternal-api.aeropost.com',
        'client_id': 'exposervice',
        'client_secret': 'iWmIn2rxR0wEmciMvGeg6orRO1PcoNvL',
        'username': '105760',
        'password': 'vwxk8295VW',
        'gateway': 'SCL'
    }

    def _get_aeropost_token(self):
        try:
            config = self.AEROPOST_CONFIG
            credentials = f"{config['client_id']}:{config['client_secret']}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            auth_url = f"{config['auth_url']}/auth/realms/myaccount/protocol/openid-connect/token"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {encoded_credentials}'
            }
            data = {
                'grant_type': 'password',
                'scope': 'openid email',
                'username': config['username'],
                'password': config['password'],
                'gateway': config['gateway']
            }
            _logger.info("Solicitando token AeroPost...")
            response = requests.post(auth_url, data=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                _logger.info("Token AeroPost obtenido exitosamente")
                return token_data['access_token']
            else:
                _logger.error(f"Error obteniendo token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"Excepción obteniendo token: {str(e)}")
            return None

    def _get_package_info(self, aerotrack_code):
        try:
            access_token = self._get_aeropost_token()
            if not access_token:
                _logger.error("No se pudo obtener token de acceso")
                return None

            config = self.AEROPOST_CONFIG
            package_url = f"{config['api_url']}/api/v2/packages/{aerotrack_code}"

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            _logger.info(f"Consultando paquete: {aerotrack_code}")
            response = requests.get(package_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                package_data = response.json()
                _logger.info(f"Paquete {aerotrack_code} encontrado")
                return package_data
            elif response.status_code == 404:
                _logger.warning(f"Paquete {aerotrack_code} no encontrado")
                return None
            else:
                _logger.error(f"Error consultando paquete {aerotrack_code}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"Excepción consultando paquete {aerotrack_code}: {str(e)}")
            return None

    def _get_reference_from_mia(self, mia_code):
        if not mia_code.startswith('MIA'):
            return None
            
        package_data = self._get_package_info(mia_code)
        if package_data:
            reference = package_data.get('courierTracking')
            _logger.info(f"Referencia extraída de courierTracking: {reference}")
            
            if reference and reference != 'N/A' and reference != 'None':
                _logger.info(f"Referencia encontrada: {reference} para MIA {mia_code}")
                return reference
            else:
                _logger.warning(f"Paquete encontrado pero courierTracking vacío o inválido: {reference}")
        else:
            _logger.warning(f"No se pudo obtener información del paquete para MIA {mia_code}")
        
        return None

    def _format_package_status(self, package_data):
        if not package_data:
            return "No encontrado en AeroPost"
        
        try:
            aerotrack = package_data.get('aerotrack', 'N/A')
            status_name = package_data.get('statusName', 'N/A')
            status_code = package_data.get('statusCode', 'N/A')
            last_update = package_data.get('lastUpdate', 'N/A')
            store = package_data.get('store', 'N/A')
            description = package_data.get('description', 'N/A')
            courier_name = package_data.get('courierName', 'N/A')
            courier_tracking = package_data.get('courierTracking', 'N/A')
            
            if last_update and last_update != 'N/A':
                try:
                    date_obj = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                    last_update = date_obj.strftime('%d/%m/%Y %H:%M:%S')
                except:
                    pass
            
            status_color = "blue"
            status_detail = package_data.get('statusDetail', {})
            if status_detail:
                detail_color = status_detail.get('color', '').lower()
                if detail_color == 'red':
                    status_color = "red"
                elif detail_color == 'green':
                    status_color = "green"
                elif detail_color == 'yellow':
                    status_color = "orange"
            
            html_status = f"""
            <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-bottom: 10px; background-color: #f9f9f9;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="color: {status_color}; font-size: 14px;">{status_name}</strong>
                    <span style="font-size: 12px; color: #666;">Código: {status_code}</span>
                </div>
                <div style="font-size: 12px; color: #666;">
                    <div><strong>Referencia:</strong> {courier_tracking}</div>
                    <div><strong>MIA:</strong> {aerotrack}</div>
                    <div><strong>Tienda:</strong> {store}</div>
                    <div><strong>Descripción:</strong> {description}</div>
                    <div><strong>Courier:</strong> {courier_name}</div>
                    <div><strong>Última actualización:</strong> {last_update}</div>
                </div>
            </div>
            """
            return html_status
            
        except Exception as e:
            _logger.error(f"Error formateando estado: {str(e)}")
            return f"Error procesando información del paquete"

    def get_aerotrack_codes_list(self):
        self.ensure_one()
        if not self.x_aerotrack:
            return []
        
        text = self.x_aerotrack.replace('\n', ',').replace(';', ',')
        codes = [code.strip().upper() for code in text.split(',') if code.strip()]
        return codes

    def get_status_by_aerotrack(self, aerotrack_code):
        package_data = self._get_package_info(aerotrack_code)
        return self._format_package_status(package_data)

    @api.depends('x_aerotrack')
    def _compute_estado_pedido(self):
        for order in self:
            if order.x_aerotrack:
                codes = order.get_aerotrack_codes_list()
                estados_html = []
                
                for code in codes:
                    if code.startswith('MIA'):
                        status_html = order.get_status_by_aerotrack(code)
                        estados_html.append(f"""
                        <div style="margin-bottom: 15px;">
                            <div style="font-weight: bold; font-size: 14px; margin-bottom: 5px;">{code}</div>
                            {status_html}
                        </div>
                        """)
                    else:
                        estados_html.append(f"""
                        <div style="margin-bottom: 10px;">
                            <div style="font-weight: bold; font-size: 14px; margin-bottom: 5px;">{code}</div>
                            <div style="color: #666; font-style: italic;">Código no MIA - Sin seguimiento disponible</div>
                        </div>
                        """)
                
                if estados_html:
                    order.x_estado_pedido = ''.join(estados_html)
                    order.x_aeropost_last_sync = datetime.now()
                else:
                    order.x_estado_pedido = '<div style="color: #666;">Sin códigos válidos para consultar</div>'
            else:
                order.x_estado_pedido = '<div style="color: #666;">Ingrese códigos Aerotrack</div>'

    def _cancel_and_delete_order(self, order):
        try:
            order_name = order.name
            order_id = order.id
            
            if order.state != 'cancel':
                _logger.info(f"Cancelando pedido {order_name}...")
                order.button_cancel()
                _logger.info(f"Pedido {order_name} cancelado")
            
            _logger.info(f"Eliminando pedido {order_name}...")
            order.unlink()
            _logger.info(f"Pedido {order_name} (ID: {order_id}) eliminado correctamente")
            
            return True
            
        except Exception as e:
            _logger.error(f"Error cancelando/eliminando pedido {order.name}: {str(e)}")
            return False

    def buscar_pedido_por_mia(self):
        if not self.x_aerotrack:
            raise UserError("Ingrese un código MIA primero")
        
        codes = self.get_aerotrack_codes_list()
        
        for code in codes:
            if code.startswith('MIA'):
                reference = self._get_reference_from_mia(code)
                
                if reference:
                    _logger.info(f"Buscando PEDIDO DE COMPRA con referencia: {reference}")
                    
                    existing_order = self.search([
                        ('partner_ref', '=', reference)
                    ], limit=1)
                    
                    if existing_order:
                        _logger.info(f"PEDIDO existente encontrado: {existing_order.name} - Vendedor: {existing_order.partner_id.name} - Estado: {existing_order.state}")
                        
                        order_vals = {
                            'partner_ref': reference,
                            'partner_id': existing_order.partner_id.id,
                            'date_order': existing_order.date_order,
                            'date_approve': existing_order.date_approve,
                            'currency_id': existing_order.currency_id.id,
                            'company_id': existing_order.company_id.id,
                            'x_aerotrack': code,
                            'state': existing_order.state,
                        }

                        if existing_order.order_line:
                            order_lines = []
                            for line in existing_order.order_line:
                                line_vals = {
                                    'product_id': line.product_id.id,
                                    'name': line.name,
                                    'product_qty': line.product_qty,
                                    'product_uom': line.product_uom.id,
                                    'price_unit': line.price_unit,
                                    'date_planned': line.date_planned,
                                }
                                order_lines.append((0, 0, line_vals))
                            order_vals['order_line'] = order_lines
                        
                        order_name_to_delete = existing_order.name
                        if not self._cancel_and_delete_order(existing_order):
                            raise UserError(f"No se pudo cancelar/eliminar el pedido anterior {order_name_to_delete}")
                        
                        _logger.info(f"Creando NUEVO pedido con datos del anterior...")
                        new_order = self.create(order_vals)
                        
                        _logger.info(f"NUEVO pedido creado: {new_order.name} con:")
                        _logger.info(f"   - MIA: {code}")
                        _logger.info(f"   - Vendedor: {new_order.partner_id.name}")
                        _logger.info(f"   - Fecha orden: {new_order.date_order}")
                        _logger.info(f"   - Fecha aprobación: {new_order.date_approve}")
                        _logger.info(f"   - Estado: {new_order.state}")
                        
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'purchase.order',
                            'res_id': new_order.id,
                            'views': [[False, 'form']],
                            'target': 'current',
                            'context': {'form_view_initial_mode': 'edit'}
                        }
                    else:
                        _logger.info(f"Creando NUEVO pedido con referencia: {reference}")                        
                        similar_orders = self.search([
                            ('partner_ref', 'ilike', reference[:10])
                        ], limit=1)
                        
                        if similar_orders:
                            suggested_vendor = similar_orders.partner_id
                            _logger.info(f"Vendedor sugerido: {suggested_vendor.name}")
                        else:
                            last_order = self.search([], order='id desc', limit=1)
                            suggested_vendor = last_order.partner_id if last_order else False
                        
                        new_order = self.create({
                            'partner_ref': reference,
                            'partner_id': suggested_vendor.id if suggested_vendor else False,
                            'x_aerotrack': code,
                        })
                        _logger.info(f"NUEVO pedido creado: {new_order.name} con Vendedor: {new_order.partner_id.name if new_order.partner_id else 'Por asignar'}")
                        
                        return {
                            'type': 'ir.actions.act_window',
                            'res_model': 'purchase.order',
                            'res_id': new_order.id,
                            'views': [[False, 'form']],
                            'target': 'current',
                            'context': {'form_view_initial_mode': 'edit'}
                        }
                else:
                    raise UserError(f"No se pudo obtener la referencia para el MIA: {code}")
        
        raise UserError("No se encontró ningún código MIA válido")

    def action_auto_complete_from_mia(self):
        if self.x_aerotrack and not self.partner_ref and not self.id:
            codes = self.get_aerotrack_codes_list()
            for code in codes:
                if code.startswith('MIA'):
                    reference = self._get_reference_from_mia(code)
                    if reference:
                        self.partner_ref = reference                        
                        existing_order = self.search([
                            ('partner_ref', '=', reference)
                        ], limit=1)
                        
                        if existing_order:
                            self.partner_id = existing_order.partner_id
                            _logger.info(f"Vendedor auto-completado: {existing_order.partner_id.name}")
                        break

    @api.onchange('x_aerotrack')
    def _onchange_x_aerotrack(self):
        if not self.id:
            codes = self.get_aerotrack_codes_list()
            for code in codes:
                if code.startswith('MIA'):
                    reference = self._get_reference_from_mia(code)
                    if reference:
                        existing_order = self.search([
                            ('partner_ref', '=', reference)
                        ], limit=1)
                        
                        if existing_order:
                            self.partner_id = existing_order.partner_id
                            return {
                                'warning': {
                                    'title': 'Pedido Existente Encontrado',
                                    'message': f'Ya existe el pedido {existing_order.name} con esta referencia y vendedor {existing_order.partner_id.name}.\n\nAl usar "Buscar Pedido por MIA" se creará un NUEVO pedido y se ELIMINARÁ el anterior {existing_order.name}.'
                                }
                            }
                        else:
                            self.partner_ref = reference
                            _logger.info(f"Referencia auto-completada: {reference}")
                    break

    def cron_update_aerotrack_status(self):
        try:
            orders = self.search([('x_aerotrack', '!=', False)])
            update_count = 0
            _logger.info(f"Iniciando actualización automática de {len(orders)} pedidos")
            
            for order in orders:
                try:
                    old_status = order.x_estado_pedido
                    order._compute_estado_pedido()
                    
                    if old_status != order.x_estado_pedido:
                        update_count += 1
                        _logger.info(f"Actualizado pedido {order.name}")
                        
                except Exception as e:
                    _logger.error(f"Error actualizando pedido {order.name}: {str(e)}")
                    continue
            
            _logger.info(f"Cron completado: {len(orders)} pedidos revisados, {update_count} actualizados")
            
        except Exception as e:
            _logger.error(f"Error en cron: {str(e)}")
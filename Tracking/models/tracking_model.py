import os
import xlrd
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class TrackingExcel(models.Model):
    _name = 'tracking.excel'
    _description = 'Gestion de archivos Excel de tracking'

    tracking_number = fields.Char(string='Numero de Tracking')

    def search_tracking(self):
        self.ensure_one()
        try:
            excel_path = r'C:\Program Files\server\custom_addons\Tracking\download'
            
            if not os.path.exists(excel_path):
                raise UserError(_("La carpeta de descarga no existe: %s") % excel_path)
            
            excel_files = [f for f in os.listdir(excel_path) if f.endswith(('.xlsx', '.xls'))]
            
            if not excel_files:
                raise UserError(_("No se encontraron archivos Excel en la carpeta de descarga"))
            
            latest_file = max(excel_files, key=lambda f: os.path.getmtime(os.path.join(excel_path, f)))
            file_path = os.path.join(excel_path, latest_file)
            
            workbook = xlrd.open_workbook(file_path)
            sheet = workbook.sheet_by_index(0)
            
            headers = [sheet.cell_value(0, col) for col in range(sheet.ncols)]
            
            if 'Aerotrack' not in headers:
                raise UserError(_("No se encontro la columna 'Aerotrack' en el archivo Excel"))
            
            aerotrack_col = headers.index('Aerotrack')
            
            result_row = None
            for row_idx in range(1, sheet.nrows):
                cell_value = sheet.cell_value(row_idx, aerotrack_col)
                if str(cell_value) == str(self.tracking_number):
                    result_row = row_idx
                    break
            
            if result_row is None:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Resultado de Búsqueda'),
                        'message': _('Tracking number no encontrado'),
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            
            row_data = {}
            for col_idx, header in enumerate(headers):
                cell_value = sheet.cell_value(result_row, col_idx)
                if cell_value and isinstance(cell_value, float):
                    try:
                        cell_value = xlrd.xldate_as_datetime(cell_value, workbook.datemode)
                        cell_value = cell_value.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                row_data[header] = cell_value
            
            message_html = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                <div style="margin-bottom: 15px;">
                    <strong">📦 Numero de Tracking:</strong><br/>
                    <span style="font-size: 16px; font-weight: bold; color: #28a745;">{row_data.get('Aerotrack', 'N/A')}</span>
                </div>
                
                <div style="margin-bottom: 12px;">
                    <strong>📝 Descripcion:</strong><br/>
                    <span style="font-size: 14px;">{row_data.get('Description', 'N/A')}</span>
                </div>
                
                <div style="margin-bottom: 12px;">
                    <strong>🔄 Estado:</strong><br/>
                    <span style="font-size: 14px;">{row_data.get('Status', 'N/A')} - {row_data.get('Stage', 'N/A')}</span>
                </div>
                
                <div style="margin-bottom: 12px;">
                    <strong>⏰ ultima Actualizacion:</strong><br/>
                    <span style="font-size: 14px;">{row_data.get('Last updated', 'N/A')}</span>
                </div>
            </div>
            """
            
            wizard = self.env['tracking.result.wizard'].create({
                'result_html': message_html
            })
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Tracking - AeroPost'),
                'res_model': 'tracking.result.wizard',
                'view_mode': 'form',
                'res_id': wizard.id,
                'target': 'new',
                'views': [(False, 'form')],
                'context': self.env.context,
            }
                
        except Exception as e:
            raise UserError(_("Error al leer el archivo Excel: %s") % str(e))
        
class TrackingResultWizard(models.TransientModel):
    _name = 'tracking.result.wizard'
    _description = 'Wizard para mostrar resultados de tracking'
    
    result_html = fields.Html(string='Resultado', readonly=True)
    
    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
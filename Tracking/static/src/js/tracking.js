odoo.define('ApiTracking.tracking', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');

    var TrackingFormController = FormController.extend({
        events: _.extend({}, FormController.prototype.events, {
            'click .btn-search-tracking': '_onSearchTracking',
        }),

        _onSearchTracking: function (ev) {
            ev.preventDefault();
            var self = this;
            var trackingNumber = this.$el.find('input[name="tracking_number"]').val();
            
            if (!trackingNumber) {
                this.do_warn('Error', 'Por favor ingrese un número de tracking');
                return;
            }

            this._rpc({
                model: 'tracking.excel',
                method: 'search_tracking',
                args: [trackingNumber],
            }).then(function (result) {
                self._displayResults(trackingNumber, result);
            }).catch(function (error) {
                self.do_warn('Error', error.message || error);
            });
        },

        _displayResults: function (trackingNumber, result) {
            var $results = this.$el.find('#tracking_results');
            
            if (result.error) {
                $results.html('<div class="alert alert-danger">' + result.error + '</div>');
                return;
            }

            if (result.found) {
                var html = '<h3>Resultados para: ' + trackingNumber + '</h3>';
                html += '<table class="table table-bordered table-striped">';
                html += '<thead><tr><th>Campo</th><th>Valor</th></tr></thead>';
                html += '<tbody>';
                
                for (var key in result.data) {
                    if (result.data.hasOwnProperty(key)) {
                        html += '<tr>';
                        html += '<td><strong>' + key + '</strong></td>';
                        html += '<td>' + (result.data[key] || 'N/A') + '</td>';
                        html += '</tr>';
                    }
                }
                
                html += '</tbody></table>';
                $results.html(html);
            } else {
                $results.html('<div class="alert alert-warning">' + result.message + '</div>');
            }
        }
    });

    var TrackingFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: TrackingFormController,
        }),
    });

    viewRegistry.add('tracking_form', TrackingFormView);
});
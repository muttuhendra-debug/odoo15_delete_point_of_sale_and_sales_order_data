odoo.define('delete_pos_order_data.auto_loop', function (require) {
    "use strict";

    var FormController = require('web.FormController');

    FormController.include({
        _update: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._checkAutoLoop();
            });
        },

        on_attach_callback: function () {
            this._super.apply(this, arguments);
            this._checkAutoLoop();
        },

        _checkAutoLoop: function () {
            var self = this;
            if (this.modelName === 'delete.pos.order.wizard') {
                var state = this.renderer.state.data.state;
                if (state === 'processing') {
                    if (this.autoLoopTimer) {
                        clearTimeout(this.autoLoopTimer);
                    }
                    // Auto trigger next batch after 4 seconds (4000ms) delay as requested
                    this.autoLoopTimer = setTimeout(function () {
                        if (self.renderer && self.renderer.state && self.renderer.state.data.state === 'processing') {
                            self._callButtonAction({
                                name: 'action_process_next_batch',
                                type: 'object',
                            }, self.renderer.state);
                        }
                    }, 4000);
                } else {
                    if (this.autoLoopTimer) {
                        clearTimeout(this.autoLoopTimer);
                        this.autoLoopTimer = null;
                    }
                }
            }
        },

        destroy: function () {
            if (this.autoLoopTimer) {
                clearTimeout(this.autoLoopTimer);
                this.autoLoopTimer = null;
            }
            this._super.apply(this, arguments);
        }
    });
});

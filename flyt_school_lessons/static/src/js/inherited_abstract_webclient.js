odoo.define('flyt_school_lesson.AbstractWebClient', function (require) {
    "use strict";

    var core = require('web.core');
    var webclient = require('web.AbstractWebClient');
    var crash_manager = require('web.crash_manager')

    var _t = core._t;

    webclient.include({
        bind_events: function() {
            this._super();
            window.onerror = function (message, file, line, col, error) {
                // Scripts injected in DOM (eg: google API's js files) won't return a clean error on window.onerror.
                // The browser will just give you a 'Script error.' as message and nothing else for security issue.
                // To enable onerror to work properly with CORS file, you should:
                //   1. add crossorigin="anonymous" to your <script> tag loading the file
                //   2. enabling 'Access-Control-Allow-Origin' on the server serving the file.
                // Since in some case it wont be possible to to this, this handle should have the possibility to be
                // handled by the script manipulating the injected file. For this, you will use window.onOriginError
                // If it is not handled, we should display something clearer than the common crash_manager error dialog
                // since it won't show anything except "Script error."
                // This link will probably explain it better: https://blog.sentry.io/2016/05/17/what-is-script-error.html
                if (message != "ResizeObserver loop limit exceeded") {
                    if (message === "Script error." && !file && !line && !col && !error) {
                        if (window.onOriginError) {
                            window.onOriginError();
                            delete window.onOriginError;
                        } else {
                            crash_manager.show_error({
                                type: _t("Odoo Client Error"),
                                message: _t("Unknown CORS error"),
                                data: {debug: _t("An unknown CORS error occured. The error probably originates from a JavaScript file served from a different origin.")},
                            });
                        }
                    } else {
                        var traceback = error ? error.stack : '';
                        crash_manager.show_error({
                            type: _t("Odoo Client Error"),
                            message: message,
                            data: {debug: file + ':' + line + "\n" + _t('Traceback:') + "\n" + traceback},
                        });
                    }
                }
            };
        },
    });
});

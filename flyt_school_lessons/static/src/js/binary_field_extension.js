odoo.define('flyt_school_lessons.BinaryFieldExtension', require => {
    'use strict'
    let basic_fields = require('web.basic_fields')
    basic_fields.FieldBinaryFile.include({
        init: function () {
            this._super.apply(this, arguments)
            this.max_upload_size = 100 * 1024 * 1024
        }
    })
})
$(document).ready(function() {
  "use strict";

  $('video').bind('contextmenu', function(e) {
      return false;
  });

  $('audio').bind('contextmenu', function(e) {
      return false;
  });
  
  var is_evaluation_view = Boolean($("input[name='fsl_not_editable']").val());
  var user_input_evaluation_type = $("input[name='user_input_evaluation_type']").val();
  var buttons = document.getElementsByName("button_submit");
  buttons.forEach(item => {
    item.disabled = true
  });
 
  if (is_evaluation_view) {
    $('form').on('submit', function (e) {
      var unevaluated_lines = $('div.evaluation-radio-group.text-center:not(:has(:radio:checked))').length;
      if (unevaluated_lines && user_input_evaluation_type !== 'teacher') {
        var num_lines_message = (`${unevaluated_lines + ' '} answer ${unevaluated_lines == 1 ? "line was " : "lines were "} not evaluated.`);
        alert("Please give an evaluation to every answer line. " + num_lines_message);
        return false;
      } else {
        return true;
      }
    });
  }

  if (!is_evaluation_view) {
    var draggables = $('.existing-attachments');
    
    draggables.each( function(i, item) {
      var drake = dragula([item]);
      
      drake.on('drop', function (el, target, source, sibling) {
        $(target).find('div.fs-story-container').each((i,el) => { 
          var obj = $(el).find('input[type="hidden"].fs-story-board');
          // split the name into sb:str, question_id:int, sort:int, img_id:int
          var name = obj.attr('name').split('_');
  
          // Change the 3rd value of the list into its new image order
          name[2] = i.toString();
          name = name.join("_");
  
          obj.attr('name', name);
          obj.attr('value', name);
        });
      });
    });  
  }
  
  $(function () {
    var html_fields = $('.html_field')
    var remarks = $('.remarks')

    window.addEventListener('DOMContentLoaded', (event) => {
      buttons.forEach(item => {
        item.disabled = false
      });
    });

    if (html_fields.length > 0) {
      var height = 350;
      if (remarks.length > 0) {
        height = 250;
      }
      
      tinymce.init({
        selector: '.html_field',
        menubar: false,
        height: height,
        plugins: 'table lists advlist wordcount',
        toolbar: 'undo redo | styleselect | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | table'
      });
      $('.btn').click(function() {
        html_fields.each(function (index, html_field) {
          var value = html_field.previousSibling.firstChild.children[1].firstChild.contentDocument.body.innerHTML;
          html_field.value = value;
        });
      });
    };
    $(window).load(function() {
      // $('video').removeAttribute('autoplay');
      // $('.media_iframe_video')[0].children[2].contentDocument.body.firstChild.removeAttribute('autoplay');

      setTimeout(function() {
        var iframe_html_displays = $('.iframe_html_display')
        var parser = new DOMParser();
        if (iframe_html_displays.length > 0) {
          iframe_html_displays.each(function (index, iframe_html_display) {
            var html_output = parser.parseFromString(iframe_html_display.value[0], "text/html");
            iframe_html_display.contentDocument.firstChild.replaceWith(html_output.firstChild);
            iframe_html_display.style.height = "500px";
            iframe_html_display.setAttribute('disabled', true);
            iframe_html_display.contentDocument.firstChild.children[1].contentEditable = false;
          });
        };
        if (remarks.length > 0) {
          var value = remarks[0].attributes.value
          if (value != '') {
            var html_output = parser.parseFromString(value.nodeValue, "text/html");
            remarks[0].previousSibling.firstChild.children[1].firstChild.contentDocument.childNodes[1].replaceWith(html_output.firstChild);
            remarks[0].previousSibling.firstChild.children[1].firstChild.contentDocument.childNodes[1].childNodes[1].setAttribute('contenteditable', 'true')
          }
        };
        if (html_fields.length > 0) {
          html_fields.each(function (index, html_field) {
            var value = html_field.value
            if (value != '') {
              var html_output = parser.parseFromString(value, "text/html");
              html_field.previousSibling.firstChild.children[1].firstChild.contentDocument.childNodes[1].replaceWith(html_output.firstChild);
              html_field.previousSibling.firstChild.children[1].firstChild.contentDocument.childNodes[1].childNodes[1].setAttribute('contenteditable', 'true')
            }
          });
        }
        var videos = document.getElementsByTagName("video")
        if (videos.length > 0) {
          for (var video of videos) {
            if (video.controls != true) {
              video.setAttribute('controls', 'controls');
              video.setAttribute('controlsList', 'nodownload');
            }
          };
        }
      }, 300);
    });
  });
});

$(document).ready(function() {
    
    $("img[name^='eval_icon_']").each(function(i,element) {
        var color = $(element).data('hover_color')
        var name = $(element).data('evaluation_name')
        var description = $(element).data('evaluation_description')

        $(element).tooltip({
            tooltipClass: "tooltip",
            title: description
        })

        $(element).click(function(){
            $(this).parent().parent().find('span[name^="evaluation_criteria_title_"]').text(name)
            $(this).parent().parent().find('span[name^="evaluation_criteria_title_"]').css({
                "color": color,
                "font-weight": "bold"
            })

            $(this).parent().parent().find('img').each(function(i,element) {
                $(element).css("background-color", "")
            })

            $(this).css({
                "background-color": color,
                "border-radius": "150px"
            })

            $(this).unbind("mouseenter mouseleave")

        }) 

        $(element).hover(function(){
            $(this).css({
                "background-color": color, 
                "transition": "all 0.5s ease",
                "border-radius": "150px"
            })
        }, function(){
            $(this).css("background-color", "")
        })

    })

    $("div.evaluation-view-radio-group.text-center").each(function(i,element) {
        var evaluator_evaluation = $(element).data('eval_answers')

        $(element).find("img[eval_id='"+evaluator_evaluation+"']").click()
        $(element).find("img").off('click mouseenter mouseleave')
    })
})

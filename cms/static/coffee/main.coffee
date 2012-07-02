class @CMS
    @setHeight = =>
        windowHeight = $(this).height()
        @contentHeight = windowHeight - 29

    @bind = =>
        $('a.module-edit').click ->
            CMS.edit_item($(this).attr('id'))
            return false
        $(window).bind('resize', CMS.setHeight)

    @edit_item = (id) =>
        $.get('/edit_item', {id: id}, (data) =>
            $('#module-html').empty().append(data)
            CMS.bind()
            $('body.content .cal').css('height', @contentHeight)
            $('body').addClass('content')
            $('section.edit-pane').show()
            new Unit('unit-wrapper', id)
        )

$ ->
    $.ajaxSetup
        headers : { 'X-CSRFToken': $.cookie 'csrftoken' }
    $('section.main-content').children().hide()
    $('.editable').inlineEdit()
    $('.editable-textarea').inlineEdit({control: 'textarea'})

    heighest = 0
    $('.cal ol > li').each ->
        heighest = if $(this).height() > heighest then $(this).height() else heighest

    $('.cal ol > li').css('height',heighest + 'px')

    $('.add-new-section').click -> return false

    $('.new-week .close').click ->
        $(this).parents('.new-week').hide()
        $('p.add-new-week').show()
        return false

    $('.save-update').click ->
        $(this).parent().parent().hide()
        return false

    # $('html').keypress ->
    #   $('.wip').css('visibility', 'visible')

    setHeight = ->
        windowHeight = $(this).height()
        contentHeight = windowHeight - 29

        $('section.main-content > section').css('min-height', contentHeight)
        $('body.content .cal').css('height', contentHeight)

        $('.edit-week').click ->
            $('body').addClass('content')
            $('body.content .cal').css('height', contentHeight)
            $('section.edit-pane').show()
            return false

        $('a.week-edit').click ->
            $('body').addClass('content')
            $('body.content .cal').css('height', contentHeight)
            $('section.edit-pane').show()
            return false

        $('a.sequence-edit').click ->
            $('body').addClass('content')
            $('body.content .cal').css('height', contentHeight)
            $('section.edit-pane').show()
            return false

        $('a.module-edit').click ->
          $('body.content .cal').css('height', contentHeight)

    $(document).ready(setHeight)
    $(window).bind('resize', setHeight)

    $('.video-new a').click ->
        $('section.edit-pane').show()
        return false

    $('.problem-new a').click ->
        $('section.edit-pane').show()
        return false
    
    CMS.setHeight()
    CMS.bind()

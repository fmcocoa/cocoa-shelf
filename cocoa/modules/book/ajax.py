# -*- coding: utf-8 -*-
from flask.ext.login import current_user, login_required
from flask.ext.babel import gettext as _

from cocoa.helpers.common import str2list
from .models import Book
from ..colist.models import Colist

class AjaxActions(object):

    @staticmethod
    @login_required
    def add_to_shelf(obj_response, book_id, column_names,
                     str_tags=None, short_review=None):
        """添加图书到书架"""

        book = Book.query.get_or_404(book_id)

        current_user.shelf.add_book(book, column_names) 

        if str_tags is not None:
            current_user.add_booktags(book, str2list(str_tags))

        if short_review is not None:
            current_user.publish_short_review(book, short_review)

        obj_response.alert(_(u'Added to your shelf!'))

    @staticmethod
    def add_to_colist(obj_response, colist_id, book_id,
                      short_review=None):
        book = Book.query.get_or_404(book_id)

        colist = Colist.query.get(colist_id)
        colist.add_book(book)

        if short_review != '':
            current_user.publish_short_review(book, short_review)

        obj_response.alert(_(u'Successfully added.'))

    @staticmethod
    @login_required
    def rate(obj_response, book_id, score):
        book = Book.query.get_or_404(book_id)

        total, count = book.rate_me(score)
        average = total / count

        obj_response.script(
            u'$("#star").raty("score", ' + str(average) + ');'
            u'$("#star").raty("readOnly", true);'
            u'$("#rate-count span").html(' + str(count) + ');'
            u'$("#my-score").html("我的评分：' + str(score) + u'分");'
        )

# -*- coding: utf-8 -*-
import os
import re
from time import time
from datetime import datetime
from PIL import Image

from werkzeug import cached_property

from sqlalchemy import or_
from sqlalchemy.ext.associationproxy import association_proxy

from flask import current_app, url_for
from flask.ext.babel import gettext as _
from flask.ext.login import current_user
from flask.ext.sqlalchemy import BaseQuery

from cocoa.extensions import db
from cocoa.helpers.sql import JSONEncodedDict
from cocoa.helpers.html import safe_html
from cocoa.helpers.upload import mkdir
from .consts import Currency, Binding, Language
from .helpers import isbn10_to_13, isbn13_to_10
from ..tag.models import Tag, BookTags
from ..bookrate.models import BookRate, BookRateDetail
from ..recsys.book import SimilarBooks

class BookExtra(db.Model):
    """内容简介，作者简介"""

    __tablename__ = 'book_extra'

    book_id = db.Column(db.Integer, db.ForeignKey('book.id'),
        primary_key=True)
    summary = db.Column(db.Text)
    author_intro = db.Column(db.Text)
    catalog = db.Column(db.Text)

    book = db.relationship('Book',
        backref=db.backref('extra', cascade='all, delete-orphan',
        uselist=False))

    def __init__(self, summary=None, author_intro=None, \
                 catalog=None, book=None):
        self.summary = safe_html(summary)
        self.author_intro = safe_html(author_intro)
        self.catalog = safe_html(catalog)
        self.book = book

    def get_short_summary(self):
        """100 chinese chars"""
        
        if self.summary is not None:
            if len(self.summary) > 100:
                return self.summary[:100] + '......'

        return self.summary


class BookQuery(BaseQuery):

    def get_recent_books(self, num=10):
        return self.order_by(Book.pubdate.desc()).limit(num).all()

    def get_by_isbn(self, isbn):
        return self.filter(or_(Book.isbn13==isbn,
            Book.isbn10==isbn)).first()

    def search(self, q):
        return self.filter(
                    (Book.title.like(q)  | \
                     Book.author.like(q) | \
                     Book.translator.like(q))
               ).all()


class Book(db.Model):

    __tablename__ = 'book'

    query_class = BookQuery

    id = db.Column(db.Integer, primary_key=True)
    isbn10 = db.Column(db.String(30), unique=True)
    isbn13 = db.Column(db.String(30), unique=True)

    title = db.Column(db.String(255))
    subtitle = db.Column(db.String(255))
    orititle = db.Column(db.String(255))

    size = db.Column(db.SmallInteger)
    cover = db.Column(db.String(255))
    author = db.Column(JSONEncodedDict(255))
    translator = db.Column(JSONEncodedDict(255))
    publisher = db.Column(db.String(100))
    pubdate = db.Column(db.Date)

    price = db.Column(db.Float)
    currency = db.Column(db.SmallInteger, default=Currency.CNY.value)
    pages = db.Column(db.Integer)
    binding = db.Column(db.SmallInteger, default=Binding.PAPERBACK.value)
    language = db.Column(JSONEncodedDict(255),
        default=Language.CHINESE.value)

    timestamp = db.Column(db.Integer, default=int(time()))
    creator = db.Column(db.Integer, db.ForeignKey('user.id'))

    category = association_proxy('book_category', 'category')
    tags = association_proxy('book_tags', 'tag')

    def __init__(self, isbn, title, author, publisher, price=None,
                 subtitle=None, orititle=None, translator=None,
                 size=None, pubdate=None, currency=None,
                 pages=None, binding=None, language=None):
        if len(isbn) == 10:
            self.isbn10 = isbn
            self.isbn13 = isbn
        elif len(isbn) == 13:
            self.isbn13 = isbn
            self.isbn10 = isbn13_to_10(isbn)
        else:
            raise ValueError(_(u'Invalid isbn number'))

        self.title = title
        self.subtitle = subtitle
        self.orititle = orititle

        self.author = author
        self.translator = translator

        self.publisher = publisher
        self.size = size
        #self.set_pubdate(pubdate)
        self.pubdate = pubdate
        
        #self.set_price(price)
        self.price = price
        self.currency = currency
        #self.set_pages(pages)
        self.pages = pages
        #self.set_binding(binding)
        self.binding = binding
        self.language = language or Language.CHINESE.value

        #self.creator = current_user.id

    def __repr__(self):
        return '<Book %r>' % self.title

    def save(self):
        book = Book.query.filter_by(isbn13=self.isbn13).first()
        if book is not None:
            raise ValueError(_(u'We\'ve already have this book'
                               u'in our database'))
        else:
            self.timestamp = int(time())
            db.session.add(self)
            db.session.commit()

    def add_tags(self, tag_list):
        for name in tag_list:
            tag = Tag.create_or_increase(name)
            if tag in self.tags:
                book_tag = BookTags.query \
                           .filter_by(book=self, tag=tag).first()
                book_tag.increase()
            else:
                self.tags.append(tag)
                db.session.commit()

    # Deprecated
    def set_pubdate(self, pubdate):
        if pubdate is None or pubdate == '': return

        if isinstance(pubdate, datetime):
            self.pubdate = pubdate
            return
        
        patterns = {
            '%Y-%m-%d': r'^(\d{4}-\d{1,2}-\d{1,2})$',     # 年月日
            '%Y-%m':    r'^(\d{4}-\d{1,2})$',             # 年月
            '%Y':       r'^(\d{4})$',                     # 年
        }

        for k in patterns.keys():
            m = re.match(patterns[k], pubdate)
            if m is not None:
                self.pubdate = datetime.strptime(m.group(1), k)
                return

    def get_price(self):
        if self.price is None:
            return None
        return str(self.price) + u'元'

    # Deprecated
    def set_price(self, price):
        if price is None or price == '': return

        if isinstance(price, (int, long, float)):
            self.price = price
            return

        re_price = '^(\d+(\.?\d{0,2})?)'
        m = re.match(re_price, price)
        if m is not None:
            self.price = float(m.group(1))

    # Deprecated
    def set_binding(self, binding):
        if binding is None or binding == '':
            self.binding = Binding.PAPERBACK.value
            return

        if isinstance(binding, (int, long)):
            self.binding = binding
            return

        try:
            self.binding = Binding.from_text(binding)
        except ValueError:
            return

    # Deprecated
    def set_pages(self, pages):
        if pages is None or pages == '': return

        if isinstance(pages, (int, long)):
            self.pages = pages
            return

        re_pages = '^(\d+)'
        m = re.match(re_pages, pages)
        if m is not None:
            self.pages = m.group(1)

    @cached_property
    def url(self):
        return url_for('book.item', book_id=self.id)

    @cached_property
    def cover_path(self):
        if self.cover:
            return current_app.config['COVER_STATIC_PATH'] + self.cover
        else:
            return ''

    def save_cover(self, cover_img):
        FORMAT = 'JPEG'
        EXTENSION = '.jpeg'

        basedir = current_app.config['COVER_BASE_DIR']
        folder = mkdir(basedir)

        cover_name = 'b' + str(self.id) + '_' + \
                     str(int(time())) + EXTENSION
        cover_path = os.path.join(folder, cover_name)

        cover_img.save(os.path.join(basedir, cover_path),
                       FORMAT, quality=100)
        
        # delete old
        if self.cover is not None:
            old = os.path.join(basedir, self.cover)
            if os.path.isfile(old):
                os.remove(old)

        self.cover = cover_path
        db.session.commit()

    def add_tag(self, tag_name):
        tag = Tag.create_or_increase(tag_name)
        if tag not in self.tags:
            self.tags.append(tag)
        else:
            BookTags.query.filter_by(book=self, tag=tag).first().increase()

        return tag

    def set_category(self, category):
        self.category = category
        db.session.commit()

    def rate_me(self, score):
        my_rate = BookRateDetail.query.filter_by(book_id=self.id,
            user_id=current_user.id).first()

        if my_rate is not None:
            return
        else:
            rate_detail = BookRateDetail(int(score), current_user, self)
            rate_detail.save()

        return self.rate.total, self.rate.count

    def my_rate(self):
        mine = BookRateDetail.query.filter_by(book_id=self.id,
            user_id=current_user.id).first()
        return mine

    def get_rate_count(self):
        return BookRateDetail.query.filter_by(book_id=self.id).count()

    def who_have(self, num=None):
        from ..shelf.models import ColumnHave
        return ColumnHave.who_have(self.id)

    def how_many_have(self):
        from ..shelf.models import ColumnHave
        return ColumnHave.how_many_have(self.id)

    def who_like(self, num=None):
        from ..shelf.models import ColumnLike
        return ColumnLike.who_like(self.id)

    def how_many_like(self):
        from ..shelf.models import ColumnLike
        return ColumnLike.how_many_like(self.id)

    def get_similar_books(self):
        books = []
        # TODO
        #for x in self.similar_books.similarity:
        #    books.append(Book.query.get(x[0]))
        return books

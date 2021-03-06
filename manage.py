# -*- coding: utf-8 -*-
from flask import current_app
from flask.ext.script import Manager, prompt_bool

from sphinx.websupport import WebSupport

from cocoa import create_app
from cocoa.extensions import db

from cocoa.modules.location.models import IpSection, City, Province
from cocoa.modules.account.models import User, SignupConfirm
from cocoa.modules.book.models import Book, BookExtra
from cocoa.modules.category.models import Category, BookCategory
from cocoa.modules.tag.models import Tag, BookTags, UserBookTags
from cocoa.modules.shelf.models import Shelf, ColumnHave, \
        ColumnRead, ColumnReading, ColumnWish, ColumnLike
from cocoa.modules.event.models import EventRecord
from cocoa.modules.bookrate.models import BookRateDetail, BookRate
from cocoa.modules.blog.models import Post, Keyword, PostKeywords
from cocoa.modules.colist.models import Colist, ColistBooks
from cocoa.modules.mail.models import Mail, MailInbox
from cocoa.modules.comment.models import ShelfComments, \
        BookShortReview
from cocoa.modules.follower.models import Follower
from cocoa.modules.group.models import Group, GroupUsers, \
        GroupTopics, GroupTopicReplies, GroupApplicant
from cocoa.modules.recsys.tag import SimilarTags
from cocoa.modules.recsys.book import SimilarBooks
from cocoa.modules.vitality.models import UserVitality
from cocoa.modules.bookstore.models import Bookstore
from cocoa.modules.photoalbum.models import Album, AlbumPhotos

manager = Manager(create_app())

@manager.command
def db_create_all():
    """创建数据表"""

    db.create_all()


@manager.command
def db_drop_all():
    """移除所有数据表"""

    if prompt_book("Are you sure? You will lose all your data!"):
        db.drop_all()


@manager.command
def docs_build():
    """创建文档"""

    docs_dir = current_app.config['DOCS_DIR']
    from os.path import join
    support = WebSupport(srcdir=docs_dir,
                         builddir=docs_dir,
                         staticroot='docs/static')
    support.build()


@manager.shell
def make_shell_context():
    return dict(app=current_app,
                db=db,
                Book=Book,
                User=User,)

if __name__ == '__main__':
    manager.run()

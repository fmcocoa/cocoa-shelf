# -*- coding: utf-8 -*-
import os
from time import time

from werkzeug import cached_property

from flask.ext.sqlalchemy import BaseQuery

from cocoa.extensions import db, album as album_set
from cocoa.helpers.upload import mkdir

class AlbumPhotos(db.Model):

    __tablename__ = 'album_photos'

    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.Integer, db.ForeignKey('album.id'))
    filename = db.Column(db.String(100))
    timestamp = db.Column(db.Integer, default=int(time()))

    album = db.relationship('Album',
        backref=db.backref('photos', cascade='all, delete-orphan'))

    def __init__(self, filename, album=None):
        self.filename = filename
        self.album = album

    @cached_property
    def url(self):
        return os.path.join(self.album.path, self.filename)


class AlbumQuery(BaseQuery):

    def user_default_album(self, user):
        return self.filter(Album.user==user).\
               filter(Album.default==True).first()


class Album(db.Model):

    __tablename__ = 'album'

    query_class = AlbumQuery

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    folder = db.Column(db.String(100))
    count = db.Column(db.SmallInteger, default=0)
    default = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.Integer, default=int(time()))

    user = db.relationship('User',
        backref=db.backref('albums', cascade='all, delete-orphan'))

    def __init__(self, name, default=False, user=None):
        self.name = name
        self.user = user
        self.default = default

        basedir = album_set.config.destination
        parent_folder = mkdir(basedir)
        folder = mkdir(os.path.join(basedir, parent_folder))
        self.folder = os.path.join(parent_folder, folder)

    def __repr__(self):
        return '<Album %r>' % self.name

    def add_photo(self, src):
        self.photos.append(AlbumPhotos(src))
        db.session.commit()

    @cached_property
    def path(self):
        return '/static/upload/album/' + self.folder

from aiohttp import web

from final.api.views import search_view, signup_view, login_view


app = web.Application()
app.add_routes([
    web.get('/search', search_view),
    web.post('/signup', signup_view),
    web.post('/login', login_view)
])

web.run_app(app)

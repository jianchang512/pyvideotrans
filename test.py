from elevenlabs import voices, set_api_key

set_api_key('f9501890a53212e9c7c28fca90398207')

voiceslist = voices()

print(voiceslist)
# Copyright 2015 Metaswitch Networks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM alpine:edge 

# Install the system packages needed for building the PyInstaller based binary
RUN apk -U add --virtual temp python-dev py-pip alpine-sdk python 

# Install python dependencies
RUN pip install datetime requests 

ADD getter.py /getter.py

CMD ["/usr/bin/python", "/getter.py"]

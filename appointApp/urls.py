from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    ######################### Patient Appointments ############################  
    path("get_doctor_appointments/",get_doctor_appointments,name='get_doctor_appointments'),
    path("update_appointment_status",update_appointment_status),
    path("cancel_appointment/",cancel_appointment),
    path("insert_appointment_data/",insert_appointment_data),
    path('get_patient_by_appointment_id/',get_patient_by_appointment_id),
    path("update_appointment_by_id/",update_appointment_by_id),
   
]
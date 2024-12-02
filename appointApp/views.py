from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework import status
from datetime import datetime
from rest_framework.views import APIView
from rest_framework import serializers
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view
from django.db import transaction
from django.db import models
from django.shortcuts import get_object_or_404
from django.http import Http404
from medicify_project.models import * 
from medicify_project.serializers import *
from django.db import connection

# Create your views here.

######################### DOCTOR APPOINTMENT ###################################
###################### GET ##################
@api_view(['GET'])
def get_doctor_appointments(request):
    response_data = {
        'message_code': 999,
        'message_text': 'Functional part is commented.',
        'message_data': [],
        'message_debug': ""
    }

    doctor_id = request.data.get('Doctor_Id', '')
    appointment_date_time = request.data.get('Appointment_DateTime', '')

    if not doctor_id:
        response_data = {'message_code': 999, 'message_text': 'Doctor id is required.'}
    elif not appointment_date_time:
        response_data = {'message_code': 999, 'message_text': 'Appointment Date and Time is required.'}
    else:
        try:
            # Convert provided datetime to start and end timestamps
            appointment_date_time_s = datetime.strptime(appointment_date_time, '%Y-%m-%d %H:%M:%S').replace(hour=0, minute=0, second=0)
            appointment_date_time_e = datetime.strptime(appointment_date_time, '%Y-%m-%d %H:%M:%S').replace(hour=23, minute=59, second=59)

            # Fetch data using Django ORM
            appointments = Tbldoctorappointments.objects.filter(
                Q(appointment_datetime__gte=appointment_date_time_s.timestamp()) &
                Q(appointment_datetime__lte=appointment_date_time_e.timestamp()) &
                Q(doctor_id=doctor_id) &
                Q(isdeleted=0)
            )

            # Serialize the data
            serializer = TbldoctorappointmentsSerializer(appointments, many=True)
            result = serializer.data
            
            if result:
                response_data = {
                    'message_code': 1000,
                    'message_text': "Appointment information retrieved successfully.",
                    'message_data': result,
                    'message_debug': ""
                }
            else:
                response_data = {
                    'message_code': 999,
                    'message_text': "Appointments for this doctor ID not found.",
                    'message_data': [],
                    'message_debug': ""
                }

        except Exception as e:
            response_data = {'message_code': 999, 'message_text': f"Error: {str(e)}"}

    return Response(response_data, status=status.HTTP_200_OK)

###################### Update ##################
@api_view(['POST'])
def update_appointment_status(request):
    response_data = {
        'message_code': 999,
        'message_text': 'Functional part is commented.',
        'message_data': [],
        'message_debug': ""
    }

    # Extract data from request
    appointment_id = request.data.get('appointment_id', '')
    appointment_status = request.data.get('appointment_status', '')

    # Validate appointment_id
    if not appointment_id:
        response_data = {'message_code': 999,'message_text': 'Appointment Id is required'}

    # Validate appointment_status
    elif not appointment_status:
        response_data = {'message_code': 999,'message_text': 'Appointment Status is required'}
         
    else:
        try:
            # Retrieve the appointment instance using ORM
            appointment = Tbldoctorappointments.objects.get(appointment_id=appointment_id)

            # Update the appointment status
            appointment.appointment_status = appointment_status
            appointment.save()

            response_data = {
                'message_code': 1000,
                'message_text': 'Appointment Status updated successfully',
                'message_data':"Appointment Id: "+ str(appointment_id),
                'message_debug': ""
            }

        except Tbldoctorappointments.DoesNotExist:
            response_data = {'message_code': 999, 'message_text': 'Appointment not found'}

        except Exception as e:
            response_data = {'message_code': 999, 'message_text': f'Error: {str(e)}'}

    return Response(response_data, status=status.HTTP_200_OK)

###################### DELETE ##################
@api_view(['DELETE'])
def cancel_appointment(request):
    response_data = {
        'message_code': 999,
        'message_text': 'Functional part is commented.',
        'message_data': [],
        'message_debug': ""
    }

    # Extract data from request
    appointment_id = request.data.get('appointment_id', None)

    # Validate appointment_id
    if not appointment_id:
        response_data={'message_code': 999, 'message_text': 'Appointment id is required'}
    
    else:
        try:
            # Retrieve the appointment instance using ORM
            appointment = Tbldoctorappointments.objects.get(appointment_id=appointment_id)

            # Set IsDeleted flag to 1
            appointment.isdeleted = 1
            appointment.save()

            response_data = {
                'message_code': 1000,
                'message_text': 'Appointment Cancelled successfully',
                'message_data': "Appointment Id: "+ str(appointment_id),
                'message_debug': ""
            }

        except Tbldoctorappointments.DoesNotExist:
            response_data = {'message_code': 999, 'message_text': 'Appointment not found'}

        except Exception as e:
            response_data = {'message_code': 999, 'message_text': f'Error: {str(e)}'}

    return Response(response_data, status=status.HTTP_200_OK)

###################### INSERT ##################
@api_view(['POST'])
@transaction.atomic
def insert_appointment_data(request):
   
    debug = ""
    res = {'message_code': 999, 'message_text': 'Functional part is commented.', 'message_data': [], 'message_debug': debug}
     

    # Validations for required fields
    required_fields = ['doctor_id', 'appointment_datetime', 'appointment_name', 'appointment_mobileno', 'appointment_gender']
    missing_fields = [field for field in required_fields if not request.data.get(field)]

    if missing_fields:
        res['message_code'] = 999
        res['message_text'] = 'Failure'
        res['message_data'] = {f"Missing required fields: {', '.join(missing_fields)}"}

    else:
        try:
            # Convert the provided date and time to epoch time
            epoch_time = int(datetime.strptime(request.data.get('appointment_datetime'), '%Y-%m-%d %H:%M:%S').timestamp())
            current_datetime = datetime.now()

            # Get the maximum appointment token from the database
            max_appointment_token = Tbldoctorappointments.objects.filter(
                doctor_id=request.data.get("doctor_id"),
                appointment_datetime=epoch_time
            ).aggregate(max_token=models.Max('appointment_token'))['max_token']

            # Calculate the new appointment token
            appointment_token = max_appointment_token + 1 if max_appointment_token is not None else 1

            # Map gender to 0 for male and 1 for female
            gender_mapping = {'Male': 0, 'Female': 1}
            appointment_gender = gender_mapping.get(request.data.get('appointment_gender'), None)

            if appointment_gender is None:
                res['message_code'] = 999
                res['message_text'] = 'Failure'
                res['message_data'] = {'Invalid gender value'}
            else:
                
                
                data = request.data
                data['appointment_gender'] = appointment_gender
                data['appointment_token'] = appointment_token
                data['appointment_status'] = 1
                data['appointment_datetime'] = epoch_time
                 
                
                data['isdeleted'] = 0
                data['consultation_id'] = request.data.get('consultation_id')
                data['age'] = request.data.get('age')
                data['createdon']=int(current_datetime.timestamp())

                serializer = TbldoctorappointmentsSerializer(data=data)

                if serializer.is_valid():
                    instance = serializer.save()

                    last_inserted_id = instance.appointment_id

                    # last_query = connection.queries[-1]['sql']
                    # print("Last Executed Query:", last_query)

                    res = {
                        'message_code': 1000,
                        'message_text': 'Success',
                        'message_data': {'appointment_id': str(last_inserted_id)},
                        'message_debug': debug if debug else []
                    }
                else:
                    res = {
                        'message_code': 2000,
                        'message_text': 'Validation Error',
                        'message_errors': serializer.errors
                    }

        except Tbldoctorappointments.DoesNotExist:
            res = {'message_code': 999, 'message_text': 'doctorappointments not found'}

        except Exception as e:
            res = {'message_code': 999, 'message_text': f'Error: {str(e)}'}

    return Response(res, status=status.HTTP_200_OK)

@api_view(["POST"])
def get_patient_by_appointment_id(request):
        debug = []
        response_data = {
            'message_code': 999,
            'message_text': 'Functional part is commented.',
            'message_data': [],
            'message_debug': debug
        }
        appointment_id = request.data.get('appointment_id', None)

        if not appointment_id:
            response_data={'message_code': 999, 'message_text': 'appointment Id is required.'}
        
        else:
            try:
                # Get the patient complaint instance
                appointment = Tbldoctorappointments.objects.get(appointment_id=appointment_id)
                serializer = TbldoctorappointmentsSerializer(appointment)
                result = serializer.data
                    
                response_data = {
                        'message_code': 1000,
                        'message_text': 'Appointment details are fetched successfully',
                        'message_data': {'appointment details': result},
                        'message_debug': debug
                    }

            except Tbldoctorappointments.DoesNotExist:
                response_data = {'message_code': 999, 'message_text': 'Patient appointment not found.','message_debug': debug}

        return Response(response_data, status=status.HTTP_200_OK)


@api_view(["POST"])
def update_appointment_by_id(request):
    debug = []
    response_data = {
        'message_code': 999,
        'message_text': 'Functional part is commented.',
        'message_data': [],
        'message_debug': debug
    }
    
    appointment_id = request.data.get('appointment_id', None)

    if not appointment_id:
        response_data['message_text'] = 'Appointment ID is required.'
        return Response(response_data, status=status.HTTP_200_OK)

    try:
        # Get the appointment instance
        appointment = Tbldoctorappointments.objects.get(appointment_id=appointment_id)
    except Tbldoctorappointments.DoesNotExist:
        response_data['message_text'] = 'Appointment not found.'
        return Response(response_data, status=status.HTTP_200_OK)

    # Serialize the data
    serializer = TbldoctorappointmentsSerializer(appointment, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        response_data['message_code'] = 1000
        response_data['message_text'] = 'Appointment details updated successfully'
        response_data['message_data'] = {'appointment_details': serializer.data}
    else:
        response_data['message_text'] = 'Invalid data provided.'
        response_data['message_data'] = serializer.errors

    return Response(response_data, status=status.HTTP_200_OK)
